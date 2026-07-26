# tools/ (non versionné — binaires)

## Installé

| Outil | Chemin | Notes |
|-------|--------|-------|
| **AssetStudio** v2.4.1 (Razviar fork, net8.0) | [`AssetStudio/AssetStudio.GUI.exe`](AssetStudio/AssetStudio.GUI.exe) | GUI |
| | [`AssetStudio/AssetStudio.CLI.exe`](AssetStudio/AssetStudio.CLI.exe) | CLI |
| Runtime requis | .NET **8** Desktop Runtime | Déjà présent sur cette machine |

Unity cible Scrutinized : **2019.4.7f1** — couvert par ce fork.

### Usage rapide

```text
# GUI : File → Load folder → C:\Steam\steamapps\common\Scrutinized\Scrutinized_Data
tools\AssetStudio\AssetStudio.GUI.exe

# CLI : voir AssetStudio.CLI.exe --help
```

Exporter surtout : TextAsset, MonoBehaviour, Font/TMP liés UI.

## À placer (Phase 1+)

| Outil | Usage |
|-------|--------|
| **ILSpy** ou **dnSpy** | Lecture `Managed\Assembly-CSharp.dll` (Mono) |
| (optionnel) **UABE** / AssetTools.NET | Repack assets |

Ne pas copier la stack Unreal WTTG3 (`retoc`, `UAssetGUI`, `UE4SS`, `UnrealLocres`).

Scripts d’inventaire Phase 0 : `scripts/extract_browser_assets.py`, `scripts/phase0_inventory.py`.
