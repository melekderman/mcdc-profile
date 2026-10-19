# mcdc-profile

Submits profiling jobs for the problems in `tasks/serial.yaml`:

cProfile for pure Python, and profila for Numba mode.

```bash
python run.py --platform dane [--name kobayashi3-TD] [--N_particle 1e5] [--Time 1:00:00] [--output_folder] [--save_recent_output]
```

- `python` mode: `cProfile` → `profile_<N>.prof` + `profile_<N>.png` (needs `gprof2dot` and `graphviz`)
- `numba` mode: [profila](https://github.com/pythonspeed/profila) → `profile_<N>.txt` (Linux only)

Problems in `test_suite/` are taken from MC/DC `test/regression`.

## Profiled features

- `inf_shem361_td_census`: Multigroup (361 groups), infinite medium, fission, time-dependent, census + population control
- `kobayashi3-TD`: 3D plane-surface geometry with void and shield, implicit capture, time-dependent cell/mesh/global tallies
- `azurv1_census_tally`: Multigroup infinite medium (AZURV1), fission, census + population control, census-based tally
- `pincell-k_eigenvalue`: Continuous-energy neutron physics, cylinder surface, k-eigenvalue mode
- `c5g7_2d_k_eigenvalue`: Multigroup C5G7, universes + lattices, k-eigenvalue with gyration radius, population control
- `fuel_array_packaged`: Universes with rotation/translation, CylinderX/CylinderZ/Sphere surfaces
- `moving_pellet`: Moving geometry (moving pellet), cylinder surface, time-dependent fission mesh tally
- `basic_weight_windows`: Continuous-energy neutron physics, weight windows
- `cooper2`: Multigroup 2D, implicit capture + global weight roulette
- `pincell-energy_deposition`: Continuous-energy neutron physics, energy deposition tally
- `lockwood`: Electron transport, energy deposition + flux mesh tallies, surface (net current) tally
- `proton_beam`: Proton transport, condensed interactions, implicit capture, energy deposition tally

## Setup

1. **Python environment** (MC/DC requires Python >= 3.11):

   ```bash
   python3 -m venv mcdc-env
   source mcdc-env/bin/activate
   pip install --upgrade pip
   ```

2. **Clone MC/DC** (dev branch):

   ```bash
   git clone -b dev https://github.com/mcdc-project/mcdc.git
   ```

   When this suite was set up, the latest commit on `dev` was
   [`003b93a`](https://github.com/mcdc-project/mcdc/commit/003b93a31ec98dfc240fbea5b2be8ffdcd3acf30)
   (2026-10-16, "Merge pull request # 563 from nglaser3/particle-type-ww").
   To reproduce with the same version: `git -C mcdc checkout 003b93a`.

3. **Install MC/DC** in editable mode. `mpi4py` needs an MPI library, so on LC machines
   load one first (e.g., `module load mvapich2` / `openmpi`):

   ```bash
   pip install -e mcdc/
   ```

4. **Nuclear data** for the continuous-energy problems (`pincell-*`, `basic_weight_windows`,
   `lockwood`, `proton_beam`):

   ```bash
   git clone https://github.com/mcdc-project/mcdc-regression_test_data.git
   export MCDC_LIB=$PWD/mcdc-regression_test_data/
   ```

5. **cProfile** (python mode): `cProfile` comes with Python; visualization tools are 
   needed:

   ```bash
   pip install gprof2dot pyyaml matplotlib
   ```

6. **Profila** (numba mode, Linux only). See [profila](https://github.com/pythonspeed/profila)
   for details:

   ```bash
   pip install profila
   python -m profila setup
   ```

Run `run.py` from this folder in the working environment (and `MCDC_LIB` exported).
