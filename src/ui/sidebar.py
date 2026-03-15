"""The Burrow - Sidebar with lazy-loading database tree."""
from typing import Optional, Dict, Any
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from textual.message import Message


class BurrowSidebar(VerticalScroll):
    """Lazy-loading database schema tree widget."""

    DEFAULT_CSS = """
    BurrowSidebar {
        width: 30;
        border: solid $primary;
        background: $surface;
    }
    
    BurrowSidebar Tree {
        width: 1fr;
        height: 1fr;
    }
    """

    class SchemaSelected(Message):
        """Posted when a schema item is selected."""

        def __init__(self, node_type: str, path: list[str], metadata: Dict[str, Any]) -> None:
            self.node_type = node_type
            self.path = path
            self.metadata = metadata
            super().__init__()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._schema_tree: Optional[Tree] = None
        self._engine = None
        self._loaded_nodes: set[str] = set()

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        self._schema_tree = Tree("🌳 The Burrow", id="burrow-tree")
        self._schema_tree.show_root = True
        self._schema_tree.show_guides = True
        yield self._schema_tree

    def set_engine(self, engine) -> None:
        """Set the database engine and load root connections."""
        self._engine = engine
        if self._schema_tree:
            self._schema_tree.clear()
            self._schema_tree.root.set_label("🌳 The Burrow")
            self._load_root()

    def _load_root(self) -> None:
        """Load root-level connections."""
        if not self._engine:
            return

        # Add connection as root node
        connection_node = self._schema_tree.root.add(
            "🔌 Connection",
            data={"type": "connection", "path": []}
        )
        connection_node.allow_expand = True

    async def _on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle tree node expansion - lazy load children."""
        node = event.node
        node_data = node.data or {}
        node_type = node_data.get("type", "")
        node_id = id(node)

        # Prevent reloading
        if node_id in self._loaded_nodes:
            return

        self._loaded_nodes.add(node_id)

        # Load appropriate children based on node type
        if node_type == "connection":
            await self._load_databases(node)
        elif node_type == "database":
            await self._load_schemas(node)
        elif node_type == "schema":
            await self._load_tables(node)
        elif node_type == "table":
            await self._load_columns(node)

    async def _load_databases(self, node: TreeNode) -> None:
        """Load databases for a connection."""
        if not self._engine:
            return

        try:
            databases = await self._engine.get_databases()
            for db_name in databases:
                db_node = node.add(
                    f"🗄️  {db_name}",
                    data={
                        "type": "database",
                        "name": db_name,
                        "path": [db_name]
                    }
                )
                db_node.allow_expand = True
        except Exception as e:
            node.add_leaf(f"❌ Error: {str(e)}")

    async def _load_schemas(self, node: TreeNode) -> None:
        """Load schemas for a database."""
        if not self._engine:
            return

        node_data = node.data or {}
        database = node_data.get("name")

        try:
            schemas = await self._engine.get_schemas(database)
            for schema_name in schemas:
                schema_node = node.add(
                    f"📁 {schema_name}",
                    data={
                        "type": "schema",
                        "name": schema_name,
                        "database": database,
                        "path": [database, schema_name]
                    }
                )
                schema_node.allow_expand = True
        except Exception as e:
            node.add_leaf(f"❌ Error: {str(e)}")

    async def _load_tables(self, node: TreeNode) -> None:
        """Load tables for a schema."""
        if not self._engine:
            return

        node_data = node.data or {}
        database = node_data.get("database")
        schema = node_data.get("name")

        try:
            tables = await self._engine.get_tables(database, schema)
            for table_name in tables:
                table_node = node.add(
                    f"📊 {table_name}",
                    data={
                        "type": "table",
                        "name": table_name,
                        "schema": schema,
                        "database": database,
                        "path": [database, schema, table_name]
                    }
                )
                table_node.allow_expand = True
        except Exception as e:
            node.add_leaf(f"❌ Error: {str(e)}")

    async def _load_columns(self, node: TreeNode) -> None:
        """Load columns for a table."""
        if not self._engine:
            return

        node_data = node.data or {}
        database = node_data.get("database")
        schema = node_data.get("schema")
        table = node_data.get("name")

        try:
            columns = await self._engine.get_columns(database, schema, table)
            for col in columns:
                col_name = col.get("name", "")
                col_type = col.get("type", "")
                if "nullable" in col:
                    nullable = " NULL" if col["nullable"] else " NOT NULL"
                else:
                    nullable = ""
                node.add_leaf(f"🔹 {col_name} ({col_type}){nullable}")
        except Exception as e:
            node.add_leaf(f"❌ Error: {str(e)}")

    async def _on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection - post message with metadata."""
        node = event.node
        node_data = node.data or {}

        if node_data:
            self.post_message(
                self.SchemaSelected(
                    node_type=node_data.get("type", ""),
                    path=node_data.get("path", []),
                    metadata=node_data
                )
            )
