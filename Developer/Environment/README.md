# Developer Environment

Environment integration discovers local source checkouts and validates the
tools required to assemble and emulate HoloBike.

The current workstation layout is:

| Integration | Local checkout |
|---|---|
| uroborOS | `/home/odin/Documents/git_projects/os_kit/uroborOS` |
| HexAtlas | `/home/odin/Documents/git_projects/geo_kit/HexAtlas` |
| Assetscape | `/home/odin/Documents/git_projects/geo_kit/Assetscape` |
| HolobikeCore | `/home/odin/Documents/git_projects/bike_kit/HolobikeCore` |
| AthleteIdentity | `/home/odin/Documents/git_projects/id_kit/AthleteIdentity` |
| drAIs | `/home/odin/Documents/git_projects/ai_kit/drAIs` |
| HolobikeExperience | `/home/odin/Documents/git_projects/ue_kit/HolobikeExperience` |
| HolobikeDevice | `/home/odin/Documents/git_projects/ue_kit/HolobikeDevice_uplugin` |
| HolobikeRider | `/home/odin/Documents/git_projects/ue_kit/HolobikeRider_uplugin` |
| HolobikeWorlds | `/home/odin/Documents/git_projects/ue_kit/HolobikeWorlds_uplugin` |

These paths are development defaults, not deployment contracts. Future tooling
should accept an ignored local environment file under `.local/`, normalize and
validate every path, and report source revision and dirty state before invoking
any build.

Environment preflight should eventually cover required compilers, CMake,
Ninja, vcpkg, Unreal Engine, virtualization, GPU tooling, storage capacity, and
access to any explicitly selected development provider. Secrets must come from
an external secret facility and must never be written into an environment
report.
