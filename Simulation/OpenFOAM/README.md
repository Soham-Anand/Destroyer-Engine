# OpenFOAM Cases

OpenFOAM 2412 runs in a Linux container through Colima. The image is
`opencfd/openfoam-default:2412`, which publishes both `amd64` and `arm64`
variants; Docker selects the host architecture automatically.

## Start

```bash
colima start
docker compose run --rm openfoam
```

Inside the container the current directory is `/home/openfoam/cases`, which is
this folder on the host.

```bash
foamVersion
```

## Case layout

```text
Simulation/OpenFOAM/<case>/
├── 0/            # initial and boundary conditions
├── constant/     # mesh and physical properties
├── system/       # solver and numerical settings
└── README.md     # purpose, boundary conditions, solver version
```

Keep `0/`, `constant/`, `system/`, and the case README under version control.
Ignore `processor*`, `postProcessing/`, `VTK/`, and other generated output.

A case supports a design decision. Record the mesh size, boundary conditions,
solver settings, and the exact OpenFOAM version in the case README, and tag the
result `[simulated]` in the report.
