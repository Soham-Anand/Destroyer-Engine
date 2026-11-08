# Software Stack

**Status:** decided 2026-11-09  
**Applies to:** Destroyer-01(A) baseline and future Destroyer variants  
**Constraints:** macOS on Apple Silicon, zero cost, commercial-use-compatible, cross-OS preferred

This document controls the CAD, CAE, and analysis toolchain. A study that uses a different
solver must record the deviation and the reason in its report.

---

## 1. Decision

| Layer | Tool | Tested version | License | macOS | Cross-OS | Role |
|---|---|---|---|---|---|---|
| CAD | **FreeCAD** (Assembly + TechDraw + FEM workbenches) | 1.1.4 | LGPL-2.1+ | native | yes | Parametric parts, assemblies, drawings, FEA front-end |
| Code-CAD (optional) | **CadQuery** / **build123d** | current | Apache-2.0 | native | yes | Generate parts from the specification JSON; export STEP |
| Meshing | **Gmsh** | 4.15.2 | GPL-2.0+ | native | yes | STEP/IGES to CalculiX/OpenFOAM meshes |
| Structural / thermal FEA | **CalculiX** | 2.23 | GPL-2.0+ | native (`osx-arm64`) | yes | Static, modal, thermal, nonlinear |
| CFD | **OpenFOAM** (`opencfd/openfoam-default:2412`) | 2412 | GPL-3.0+ | arm64 container | Linux-first | Intake, exhaust, coolant, and external flow |
| 1-D engine simulation | **OpenWAM** | research release | GPL-3.0 | Linux/Windows via VM or container | Linux/Windows | 1-D gas dynamics; independent cross-check |
| 1-D / combustion (primary) | **Python + Cantera** | Python 3.12, Cantera 3.2.0 | BSD-3 | native (`osx-arm64`) | yes | Transparent cycle model, kinetics, equilibrium |
| Mathematics / DOE | NumPy, SciPy, pandas, matplotlib, Jupyter, Optuna | current | BSD / MIT | native | yes | Calculations, optimization, post-processing |
| Post-processing / rendering | **ParaView**, **Blender** | 6.2.0 / current | BSD-3 / GPL | native | yes | CFD post-processing, visuals |
| Data / PDM | **Git + GitHub + Git LFS**, GitHub Projects | current | free / commercial | yes | yes | Version control, BOM, issues, releases |
| Linux runtime | **Colima + Docker CLI**, **UTM** | current | MIT / Apache-2.0 | native | yes | Linux-only CAE tools on macOS |

---

## 2. Why this stack

- **FreeCAD** is the only parametric CAD that satisfies all four constraints: macOS, zero cost,
  commercial use, and Apple Silicon. It covers solid modelling, assemblies, TechDraw production
  drawings, and a CalculiX-driven FEM workbench.
- **CalculiX** is a real nonlinear FEA solver, not a toy. The conda-forge package provides a
  native `osx-arm64` build, and FreeCAD can launch it directly.
- **OpenFOAM** is industry-used CFD. The OpenCFD `2412` image publishes both `amd64` and `arm64`
  variants, so the M4 runs it natively through Colima. ParaView handles post-processing.
- **OpenWAM** is the only free, engine-specific 1-D gas-dynamics code. It is research-grade and
  no longer actively released, so it is used as an **independent reference**, not as the only
  source of truth.
- **Cantera** gives the project real thermodynamics and combustion kinetics while keeping the
  cycle model readable, testable, and version-controlled.
- **Python** is the glue: it reads `Specifications/destroyer-01.json`, drives the cycle model,
  writes case inputs, and post-processes results.
- **STEP AP242** is the exchange format between CAD, meshing, and FEA. Native CAD files stay in
  FreeCAD; STEP exports keep the door open to a future commercial CAD migration.

---

## 3. Licensing and commercial use

All tools in the table permit commercial use. The obligations differ:

| License family | Tools | Commercial use | Main obligation |
|---|---|---|---|
| Permissive (BSD / MIT / Apache-2.0) | Cantera, ParaView, Python libraries, CadQuery, Colima, UTM | yes | Keep notices where required |
| Weak copyleft (LGPL-2.1+) | FreeCAD | yes | Share modifications to FreeCAD itself if distributed |
| Strong copyleft (GPL-2.0+/3.0) | Gmsh, CalculiX, OpenFOAM, OpenWAM | yes | Share source of modified solver binaries if distributed |
| Proprietary service (free tier) | GitHub | yes | Accept GitHub's terms |

**Designs and simulation results are not covered by the solver licences.** Using GPL software to
design a commercial engine is permitted; the copyleft obligation applies to distribution of
modified software, not to the engine.

**Project licence:** the repository is CERN-OHL-S-2.0, a strongly reciprocal hardware licence.
Commercial use is allowed, but distributed design modifications must be shared under the same
licence. If closed-source commercialisation is required, revisit the licence before accepting
outside contributions.

---

## 4. Installation

### 4.1 Native macOS applications

```bash
brew install --cask freecad
brew install gmsh colima docker docker-compose pixi
brew install --cask paraview
```

Start the Linux container runtime:

```bash
colima start --cpu 4 --memory 8 --disk 40
```

### 4.2 Reproducible analysis environment

`pixi.toml` pins Python, NumPy, SciPy, pandas, matplotlib, JupyterLab, Cantera, and CalculiX
from conda-forge:

```bash
pixi install
pixi run test
pixi run spec
pixi run lab
```

### 4.3 OpenFOAM

```bash
docker compose run --rm openfoam
```

The service mounts `Simulation/OpenFOAM/` into the container and pins OpenFOAM 2412.

### 4.4 OpenWAM

OpenWAM is not macOS-native. Run it in a Linux VM (UTM) or a Linux container, pin the source
tarball/commit used for the study, and record that version in the simulation report. The Windows
GUI can run under a Windows VM if the graphical case builder is needed.

### 4.5 Git LFS

```bash
git lfs install
```

`.gitattributes` stores native CAD, STEP/IGES/STL, Blender files, and selected CFD post-processing
formats through Git LFS. Keep solver scratch output out of the repository.

---

## 5. Workflow

1. **Requirements and targets** — update `Specifications/destroyer-01.json` and the Markdown
   specification together.
2. **1-D cycle** — Python + Cantera model; cross-check the torque curve and volumetric efficiency
   with OpenWAM.
3. **CAD** — FreeCAD parts and assemblies; dimensions driven from the specification; export STEP
   AP242.
4. **Meshing** — Gmsh; keep the `.geo` source and the exported `.msh`.
5. **FEA** — CalculiX through FreeCAD FEM; keep the `.inp` deck and a report with boundary
   conditions.
6. **CFD** — OpenFOAM; keep `0/`, `constant/`, `system/`, and a case README; ignore processor and
   post-processing output.
7. **Validation** — compare with targets, tag results `[simulated]`, and record solver version,
   mesh, boundary conditions, and input files.

---

## 6. Repository conventions

- SI units in code and JSON. FreeCAD models may use millimetres; record the conversion.
- Native CAD: `CAD/Components/`, `CAD/Assemblies/`, `CAD/Drawings/`.
- Exchange CAD: STEP AP242, exported from FreeCAD; do not edit STEP as the source of truth.
- Part naming follows `CAD/README.md`: `Destroyer-01-<system>-<part>-<revision>.<ext>`.
- Simulation cases live under `Simulation/<solver>/<case>/`; keep inputs and a README, ignore
  heavy output.
- Every study records the exact tool versions in its report; update this document when a version
  changes deliberately.

---

## 7. Rejected alternatives

| Tool | Reason rejected |
|---|---|
| SolidWorks for Makers | Windows-only, annual fee, non-commercial licence |
| Fusion 360 Personal | Free but non-commercial; cloud lock-in |
| Onshape Free | Non-commercial and all documents public; Standard is $1,500/user/year |
| Ansys Student | Windows-only; educational use only |
| SimScale Community | Free for testing and learning; not commercial; limited physics |
| GT-Power / AVL BOOST / Ricardo WAVE | Industry standard, but paid, Windows, institution-only academic licences |
| MATLAB / Simulink | Paid; Python and OpenModelica cover the same ground |

---

## 8. Review triggers

Revisit this decision if any of the following becomes true:

- The assembly exceeds FreeCAD's practical assembly size or surfacing quality.
- The 1-D study cannot resolve a design decision without GT-Power/AVL BOOST-level fidelity.
- Moving-valve/piston CFD or spray combustion becomes necessary (evaluate OpenFOAM dynamic mesh,
  CONVERGE, STAR-CD, or AVL FIRE).
- Closed-source commercialisation is required (revisit CERN-OHL-S-2.0).
- A tool stops supporting Apple Silicon or its licence changes.
