"""Load and validate tile_selector configuration."""

from dataclasses import dataclass, field
from pathlib import Path

import tomllib


_CONFIG_PATH = Path(__file__).parent / "config.toml"
_ROOT_ANCHOR = ".project-root"


def _find_project_root() -> Path:
    """Walk up from this file's directory to find the .project-root anchor."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / _ROOT_ANCHOR).exists():
            return current
        current = current.parent
    raise FileNotFoundError(
        f"Project root anchor '{_ROOT_ANCHOR}' not found in any parent directory."
    )


@dataclass(frozen=True)
class Config:
    boundary_shapefile: Path
    ortho_base_dir: Path
    ortho_dir_pattern: str
    output_base_dir: Path
    boro_dir_pattern: str
    mosaic_shapefile_default: str
    mosaic_shapefile_overrides: dict[int, str]
    image_extension: str
    target_crs: int
    boundary_cd_field: str
    mosaic_image_field: str
    borough_mapping: dict[int, str] = field(default_factory=dict)

    def boro_name(self, boro_cd: int) -> str:
        """Derive borough name from a community district number."""
        leading = boro_cd // 100
        if leading not in self.borough_mapping:
            raise ValueError(
                f"Invalid boro_cd leading digit {leading} from CD {boro_cd}. "
                f"Valid: {list(self.borough_mapping.keys())}"
            )
        return self.borough_mapping[leading]

    def year_short(self, year: int) -> str:
        """Two-digit year string for path substitution."""
        return str(year % 100).zfill(2)

    def ortho_dir(self, year: int) -> Path:
        """Resolve top-level ortho directory for a given year."""
        dirname = self.ortho_dir_pattern.format(year=year)
        return self.ortho_base_dir / dirname

    def boro_dir(self, boro_cd: int, year: int) -> Path:
        """Resolve borough subdirectory within an ortho year directory."""
        name = self.boro_name(boro_cd)
        ys = self.year_short(year)
        dirname = self.boro_dir_pattern.format(boro_name=name, year_short=ys)
        return self.ortho_dir(year) / dirname

    def mosaic_shapefile_pattern(self, year: int) -> str:
        """Return the mosaic shapefile naming pattern for a given year."""
        return self.mosaic_shapefile_overrides.get(
            year, self.mosaic_shapefile_default
        )

    def mosaic_shapefile_path(self, boro_cd: int, year: int) -> Path:
        """Resolve full path to a borough's mosaic shapefile for a given year."""
        name = self.boro_name(boro_cd)
        ys = self.year_short(year)
        pattern = self.mosaic_shapefile_pattern(year)
        filename = pattern.format(boro_name=name, year_short=ys)
        return self.boro_dir(boro_cd, year) / filename

    def image_dir(self, boro_cd: int, year: int) -> Path:
        """Resolve the directory containing jp2 images for a borough/year."""
        return self.boro_dir(boro_cd, year)

    def output_dir(self, boro_cd: int, year: int) -> Path:
        """Resolve output directory for a given CD and year."""
        return self.output_base_dir / str(year) / str(boro_cd)


def load_config(config_path: Path = _CONFIG_PATH) -> Config:
    """Parse config.toml and return a validated Config instance."""
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    project_root = _find_project_root()

    borough_mapping = {
        int(k): v for k, v in raw["boroughs"]["mapping"].items()
    }

    mosaic_section = raw["paths"]["patterns"]["mosaic_shapefile"]
    mosaic_default = mosaic_section["default"]
    mosaic_overrides = {
        int(k): v for k, v in mosaic_section.items() if k != "default"
    }

    return Config(
        boundary_shapefile=project_root / raw["paths"]["boundary_shapefile"],
        ortho_base_dir=project_root / raw["paths"]["ortho_base_dir"],
        ortho_dir_pattern=raw["paths"]["patterns"]["ortho_dir"],
        output_base_dir=project_root / raw["paths"]["output_base_dir"],
        boro_dir_pattern=raw["paths"]["patterns"]["boro_dir"],
        mosaic_shapefile_default=mosaic_default,
        mosaic_shapefile_overrides=mosaic_overrides,
        image_extension=raw["paths"]["patterns"]["image_extension"],
        target_crs=raw["spatial"]["target_crs"],
        boundary_cd_field=raw["fields"]["boundary_cd_field"],
        mosaic_image_field=raw["fields"]["mosaic_image_field"],
        borough_mapping=borough_mapping,
    )