# CAD

Parametric component models, assemblies, and drawings.

## Directory roles

| Directory | Contents |
|---|---|
| `Components/` | Individual parts, modeled parametrically |
| `Assemblies/` | Subassemblies and the complete engine |
| `Drawings/` | 2-D drawings and bills of materials |

## Naming

```text
Destroyer-01-<system>-<part>-<revision>.<ext>
Destroyer-01-<part>-DWG-<revision>.<ext>
```

Example: `Destroyer-01-bottom-end-piston-r00.step` for the neutral export, with the native
parametric file using the same stem.

## Rules

- Drive primary dimensions from `Specifications/destroyer-01.json` where practical.
- Do not edit a released part without incrementing its revision.
- Run an interference check before releasing an assembly.
- Keep native CAD files and release drawings under version control; ignore application
  backup files.
- Update the mass budget whenever a part model changes.

## Status

Not started. The baseline dimensions and interfaces are available in the
[Destroyer-01 specification](../Specifications/Destroyer-01-specification.md).
