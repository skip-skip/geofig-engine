"""
Registry and Layer hydration for categorized geometry presets.

The registry indexes presets by id/category/tags and can hydrate them
into standard Layers. A module-level lazy singleton loads the bundled
preset directory; user files are merged in via merge_path().
"""

from collections.abc import Iterable, Sequence
from pathlib import Path

from geofig_engine.core.geom import (
    GeomAbline,
    GeomFunctionLine,
    GeomHSpan,
    GeomRect,
    GeomText,
    GeomVSpan,
)
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatIdentity
from geofig_engine.data.geom_presets.loader import (
    GeomPresetLoader,
    GeomPresetLoadError,
)
from geofig_engine.data.geom_presets.models import GEOM_KINDS, GeomPreset, GeomPresetItem


def _build_geom(item: GeomPresetItem):
    """Construct the core Geom for a validated preset item."""
    params = item.params
    kind = item.geom_type

    if kind == "function_line":
        return GeomFunctionLine(func=params["func"], label=item.mapping.get("label"))
    if kind == "abline":
        if "slope" in params:
            return GeomAbline(slope=params["slope"], intercept=params["intercept"])
        return GeomAbline(x1=params["x1"], y1=params["y1"], x2=params["x2"], y2=params["y2"])
    if kind == "hspan":
        return GeomHSpan()
    if kind == "vspan":
        return GeomVSpan()
    if kind == "rect":
        return GeomRect()
    if kind == "text":
        return GeomText()

    raise ValueError(f"unsupported geom_type '{kind}'")  # Defensive; models validate


def item_to_layer(item: GeomPresetItem) -> Layer:
    """Hydrate a single preset item into a Layer with constant mappings."""
    return Layer(
        geom=_build_geom(item),
        stat=StatIdentity(),
        mapping=dict(item.mapping),
        zorder=item.zorder,
    )


def preset_to_layers(preset: GeomPreset) -> list[Layer]:
    """Hydrate a preset into its list of Layers (one per item)."""
    return [item_to_layer(item) for item in preset.items]


class GeomPresetRegistry:
    """Query and manage the geom preset database."""

    def __init__(self, presets: Iterable[GeomPreset]):
        """
        Initialize registry with presets.

        Args:
            presets: Iterable of GeomPreset instances

        Raises:
            ValueError: If duplicate preset ids are supplied
        """
        self._presets: list[GeomPreset] = []
        self._by_id: dict[str, GeomPreset] = {}
        for preset in presets:
            self._add(preset)

    def _add(self, preset: GeomPreset) -> None:
        if preset.id in self._by_id:
            raise ValueError(f"Duplicate preset id: '{preset.id}'")
        self._presets.append(preset)
        self._by_id[preset.id] = preset

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, preset_id: str) -> GeomPreset:
        """
        Get a preset by ID.

        Raises:
            KeyError: If preset not found
        """
        if preset_id not in self._by_id:
            raise KeyError(f"Preset '{preset_id}' not found in registry")
        return self._by_id[preset_id]

    def get_all(self) -> list[GeomPreset]:
        """Get all presets."""
        return list(self._presets)

    def exists(self, preset_id: str) -> bool:
        """Check whether a preset id exists."""
        return preset_id in self._by_id

    def filter(
        self,
        category: str | None = None,
        tags: Sequence[str] | None = None,
        state: str | None = None,
    ) -> list[GeomPreset]:
        """
        Filter presets.

        Args:
            category: Exact category match
            tags: Preset must contain ALL of these tags
            state: Exact geospatial state match

        Returns:
            Filtered list of GeomPreset instances
        """
        results = self._presets

        if category is not None:
            results = [p for p in results if p.category == category]

        if tags is not None:
            tag_set = set(tags)
            results = [p for p in results if tag_set.issubset(set(p.tags))]

        if state is not None:
            results = [p for p in results if p.state == state]

        return list(results)

    def list_ids(self, category: str | None = None) -> list[str]:
        """List preset ids with optional category filter."""
        return [p.id for p in self.filter(category=category)]

    def get_metadata(self) -> dict:
        """Get registry statistics."""
        by_category: dict[str, int] = {}
        by_tag: dict[str, int] = {}
        by_kind: dict[str, int] = {}

        for preset in self._presets:
            by_category[preset.category] = by_category.get(preset.category, 0) + 1
            for tag in preset.tags:
                by_tag[tag] = by_tag.get(tag, 0) + 1
            for kind in preset.geom_kinds:
                by_kind[kind] = by_kind.get(kind, 0) + 1

        return {
            "total_presets": len(self._presets),
            "by_category": by_category,
            "by_tag": by_tag,
            "by_kind": by_kind,
        }

    # ------------------------------------------------------------------
    # Mutation / merging
    # ------------------------------------------------------------------

    def merge_path(self, path: Path | str, overwrite: bool = False) -> list[str]:
        """
        Merge presets from an external JSON file into this registry.

        Args:
            path: Path to a preset JSON file
            overwrite: If True, replace existing presets with conflicting ids;
                       otherwise raise on conflict

        Returns:
            List of merged preset ids (in file order)

        Raises:
            GeomPresetLoadError: If loading fails or duplicate ids exist
                without overwrite permission
        """
        incoming = GeomPresetLoader.load_file(path)

        conflicts = [p.id for p in incoming if self.exists(p.id)]
        if conflicts and not overwrite:
            raise GeomPresetLoadError(
                f"Preset id(s) already exist: {conflicts}. Pass overwrite=True to replace."
            )

        merged_ids: list[str] = []
        for preset in incoming:
            if overwrite and preset.id in self._by_id:
                index = next(i for i, p in enumerate(self._presets) if p.id == preset.id)
                self._presets[index] = preset
                self._by_id[preset.id] = preset
            else:
                self._add(preset)
            merged_ids.append(preset.id)

        return merged_ids

    # ------------------------------------------------------------------
    # Hydration
    # ------------------------------------------------------------------

    def layers_for(self, preset_ids: Sequence[str]) -> list[Layer]:
        """
        Hydrate presets by explicit IDs into Layers (in ID order).

        Raises:
            KeyError: If any ID is unknown
        """
        layers: list[Layer] = []
        for pid in preset_ids:
            layers.extend(preset_to_layers(self.get(pid)))
        return layers

    def auto_layers(self, category: str, geom_kinds: Iterable[str] | None = None) -> list[Layer]:
        """
        Hydrate all presets of a category into Layers.

        Args:
            category: Category to select
            geom_kinds: Optional whitelist; presets using other kinds are skipped

        Returns:
            List of Layers in registry order
        """
        allowed = set(geom_kinds) if geom_kinds is not None else set(GEOM_KINDS)
        selected = [p for p in self.filter(category=category) if p.geom_kinds <= allowed]
        layers: list[Layer] = []
        for preset in selected:
            layers.extend(preset_to_layers(preset))
        return layers


# Global registry instance (lazy-loaded from bundled presets)
_GLOBAL_REGISTRY: GeomPresetRegistry | None = None


def get_geom_preset_registry() -> GeomPresetRegistry:
    """
    Get or create the global geom preset registry (lazy-loaded).

    Returns:
        GeomPresetRegistry instance loaded from the bundled preset directory

    Raises:
        GeomPresetLoadError: If bundled loading fails
    """
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = GeomPresetRegistry(
            GeomPresetLoader.load_dir(GeomPresetLoader.bundled_dir())
        )
    return _GLOBAL_REGISTRY


def reset_geom_preset_registry() -> None:
    """Reset the global registry singleton (next access reloads bundled data)."""
    global _GLOBAL_REGISTRY
    _GLOBAL_REGISTRY = None
