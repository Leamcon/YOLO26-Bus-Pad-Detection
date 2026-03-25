"""Load and validate tile_selector configuration."""

from dataclasses import dataclass, field
from pathlib import Path

import tomllib


_CONFIG_PATH = Path(__file__).parent / "config.toml"


@dataclass(frozen=True)
class Config:
    boundary_shapefile: Path
    ortho_base_dir: Path
    output_base_dir: Path
    boro_dir_pattern: str
    mosaic_shapefile_pattern: str
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

    def mosaic_shapefile_path(self, boro_cd: int) -> Path:
        """Resolve full path to a borough's mosaic shapefile."""
        name = self.boro_name(boro_cd)
        boro_dir = self.boro_dir_pattern.format(boro_name=name)
        mosaic_file = self.mosaic_shapefile_pattern.format(boro_name=name)
        return self.ortho_base_dir / boro_dir / mosaic_file

    def image_dir(self, boro_cd: int) -> Path:
        """Resolve the directory containing jp2 images for a borough."""
        name = self.boro_name(boro_cd)
        boro_dir = self.boro_dir_pattern.format(boro_name=name)
        return self.ortho_base_dir / boro_dir

    def output_dir(self, boro_cd: int) -> Path:
        """Resolve output directory for a given community district."""
        return self.output_base_dir / str(boro_cd)


def load_config(config_path: Path = _CONFIG_PATH) -> Config:
    """Parse config.toml and return a validated Config instance."""
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    borough_mapping = {
        int(k): v for k, v in raw["boroughs"]["mapping"].items()
    }

    return Config(
        boundary_shapefile=Path(raw["paths"]["boundary_shapefile"]),
        ortho_base_dir=Path(raw["paths"]["ortho_base_dir"]),
        output_base_dir=Path(raw["paths"]["output_base_dir"]),
        boro_dir_pattern=raw["paths"]["patterns"]["boro_dir"],
        mosaic_shapefile_pattern=raw["paths"]["patterns"]["mosaic_shapefile"],
        image_extension=raw["paths"]["patterns"]["image_extension"],
        target_crs=raw["spatial"]["target_crs"],
        boundary_cd_field=raw["fields"]["boundary_cd_field"],
        mosaic_image_field=raw["fields"]["mosaic_image_field"],
        borough_mapping=borough_mapping,
    )