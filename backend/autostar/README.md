# autostar

Star-name cross-matching and stellar-parameter lookups for the data pipeline (`update.py`):

| Module | What it does | Reference files in `data/reference_data` |
|---|---|---|
| `simbad_query.py` | SIMBAD lookups: every catalog name of an object (`SimbadLib`) and its main record with coordinates (`SimbadMainRef`); translates current astroquery results to the format the reference files use; `SIMBAD_SERVER` picks the CDS site or the Harvard mirror | `simbad_ref_data.psv`, `simbad_main_ref_data.csv` |
| `read_gaia.py` | Gaia DR1/DR2/DR3 parameters through the ESA archive (`GaiaLib`) | `GaiaDR1_ref.csv`, `GaiaDR2_ref.csv`, `GaiaDR3_ref.csv` |
| `tic_query.py` | TESS Input Catalog parameters through MAST (`TicQuery`) | `tic_ref.csv` |
| `name_correction.py` | hand-made name fixes (`verify_starname`) and popular names (`PopNamesLib`) | `annoying_names.csv`, `popular_names.csv` |
| `bad_stars.py` | names never to query | `bad_starname_ignore.csv` |
| `import_stars.py` | `CheckStarNames`: a list of names to handles | |
| `object_params.py`, `table_read.py` | `SingleParam`, `StarDict`, CSV readers | |
| `config/datapaths.py` | file locations and the star-name grammar, imported from `ref/ref.py` and `ref/star_names.py` | |

Each lookup first checks the reference file, then queries the service; new results are appended
to the reference file, which is committed to the data repository, so a run without network access
works for every name that was seen before. Try a live lookup without writing anything:

```
docker compose run --rm backend python -m autostar.simbad_query "HD 189733"
```

## History

autostar was a separate package (PyPI `autostar`, github.com/chw3k5/autostar, Apache 2.0, the same
license as Portal) shared with HypatiaCatalog.com. Hypatia moved to its own tooling
(github.com/HypatiaOrg/HySite, `backend/hypatia/sources/simbad`) and Portal was the last user, so
the package moved here in 2026 (version 0.1.5). The modules Portal never used were left out: the
NASA Exoplanet Archive and WISE queries, a duplicate name-correction module and the default
star-name grammar, which `ref/star_names.py` replaces in full.
