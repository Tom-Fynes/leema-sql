"""Execution Plan Visualizer - Parse and render EXPLAIN output."""

from typing import Optional, Dict, Any
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode
import json


class ExecutionPlanViewer(Vertical):
    """Visual execution plan renderer."""

    DEFAULT_CSS = """
    ExecutionPlanViewer {
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    
    ExecutionPlanViewer #plan-header {
        height: 3;
        background: $boost;
        padding: 1;
    }
    
    ExecutionPlanViewer Tree {
        width: 1fr;
        height: 1fr;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._plan_tree: Optional[Tree] = None
        self.header_widget: Optional[Static] = None
        # Pending plan to show once the widget is mounted (lazy-tab scenario)
        self._pending_plan_text: Optional[str] = None
        self._pending_engine_type: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        self.header_widget = Static("🔍 Execution Plan", id="plan-header")
        yield self.header_widget

        self._plan_tree = Tree("Query Plan", id="plan-tree")
        self._plan_tree.show_root = True
        self._plan_tree.show_guides = True
        yield self._plan_tree

    def on_mount(self) -> None:
        """Flush any plan that arrived before the widget was mounted."""
        if self._pending_plan_text is not None:
            self._render_plan(
                self._pending_plan_text, self._pending_engine_type or "unknown"
            )
            self._pending_plan_text = None
            self._pending_engine_type = None

    def show_plan(self, plan_text: str, engine_type: str) -> None:
        """Parse and display execution plan."""
        if self._plan_tree is None:
            # Widget not yet mounted (lazy TabPane); store for on_mount
            self._pending_plan_text = plan_text
            self._pending_engine_type = engine_type
            return
        self._render_plan(plan_text, engine_type)

    def _render_plan(self, plan_text: str, engine_type: str) -> None:
        """Internal: populate the tree from plan_text."""
        self._plan_tree.clear()
        self._plan_tree.root.set_label(f"🔍 {engine_type.upper()} Execution Plan")

        try:
            if engine_type == "postgres":
                self._parse_postgres_plan(plan_text)
            elif engine_type in ("mssql", "sqlserver"):
                self._parse_mssql_plan(plan_text)
            elif engine_type == "duckdb":
                self._parse_duckdb_plan(plan_text)
            else:
                # Generic text plan
                self._parse_generic_plan(plan_text)
        except Exception as e:
            self._plan_tree.root.add_leaf(f"❌ Parse error: {str(e)}")

        # Expand root and all child nodes so the full plan is visible
        self._plan_tree.root.expand_all()

    def _parse_postgres_plan(self, plan_text: str) -> None:
        """Parse PostgreSQL JSON explain output."""
        try:
            plan_data = json.loads(plan_text)
            if isinstance(plan_data, list) and len(plan_data) > 0:
                plan_data = plan_data[0]

            if "Plan" in plan_data:
                self._add_postgres_node(self._plan_tree.root, plan_data["Plan"])
        except json.JSONDecodeError:
            # Fallback to text mode
            self._parse_generic_plan(plan_text)

    def _add_postgres_node(self, parent: TreeNode, node_data: Dict[str, Any]) -> None:
        """Recursively add PostgreSQL plan nodes."""
        node_type = node_data.get("Node Type", "Unknown")

        # Build label with key metrics
        cost = node_data.get("Total Cost", 0)
        rows = node_data.get("Plan Rows", 0)
        label = f"📌 {node_type} (cost={cost:.2f}, rows={rows})"

        # Add relation name if present
        if "Relation Name" in node_data:
            label += f" on {node_data['Relation Name']}"

        tree_node = parent.add(label, data=node_data)

        # Add plans recursively
        if "Plans" in node_data:
            for child_plan in node_data["Plans"]:
                self._add_postgres_node(tree_node, child_plan)

    def _parse_mssql_plan(self, plan_text: str) -> None:
        """Parse SQL Server execution plan (XML)."""
        # Simplified - in production, use xml.etree.ElementTree
        lines = plan_text.split("\n")
        for line in lines[:50]:  # Limit to first 50 lines
            if line.strip():
                self._plan_tree.root.add_leaf(line.strip())

    def _parse_duckdb_plan(self, plan_text: str) -> None:
        """Parse DuckDB execution plan.

        DuckDB EXPLAIN output uses box-drawing characters (┌ │ └) with no
        leading indentation, so every line is at the same level.  Render each
        non-blank line as a flat leaf under the root to preserve the visual
        ASCII-art tree exactly as DuckDB emits it.
        """
        for line in plan_text.split("\n"):
            if line.strip():
                self._plan_tree.root.add_leaf(line.strip())

    def _parse_generic_plan(self, plan_text: str) -> None:
        """Parse generic text execution plan."""
        lines = plan_text.split("\n")
        for line in lines:
            if line.strip():
                self._plan_tree.root.add_leaf(line.strip())

    def clear(self) -> None:
        """Clear the plan view."""
        if self._plan_tree:
            self._plan_tree.clear()
            self._plan_tree.root.set_label("Query Plan")
