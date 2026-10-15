# Autodesk real-host validation plan

## Purpose
This folder defines a truthful test boundary for Revit and AutoCAD 2016–2027. The inventory workflow does NOT claim API functionality merely because an executable or DLL exists.

## Official Autodesk implementation patterns reviewed
- Revit add-ins are registered using .addin manifests and implement IExternalCommand or IExternalApplication.
- Revit document changes must use the API transaction model; failures/cancellation should not be reported as success.
- AutoCAD managed .NET plug-ins use the supported AutoCAD .NET API; each target release must be built and tested against the matching host SDK/runtime.
- Autodesk's published compatibility guidance indicates Revit 2027 uses .NET 10, Revit 2025/2026 use .NET 8; AutoCAD 2027 plug-ins target .NET 10, 2025/2026 target .NET 8, and 2024 and earlier use .NET Framework 4.8. Exact release-specific API references must be checked before building each adapter.

## Required real-host matrix
For every year 2016–2027, separately record:
1. Installed licensed host and exact product/build version.
2. Matching SDK/API assembly versions.
3. Add-in discovery/load evidence from the host.
4. A controlled smoke command in a disposable test drawing/model.
5. A deterministic create/read/update/save/reopen assertion.
6. Error/rollback test and a clean evidence bundle.
7. Explicit NOT_RUN if the host, matching SDK, add-in, or automation harness is absent.

## Critical limitation
GitHub-hosted windows-latest runners do not automatically include licensed Revit or AutoCAD. Real-host execution requires an authorized self-hosted Windows runner with the exact products/versions installed and activated. This repository does not contain the original application source code, so this plan does not claim to repair that executable internally. Never bypass licensing, sign-in, or product activation.

## Official documentation
- Revit 2016 API introduction: https://help.autodesk.com/cloudhelp/2016/ENU/Revit-API/files/GUID-E0E0FCEB-EB88-4F15-9087-F5374817F758.htm
- Revit add-in integration: https://help.autodesk.com/cloudhelp/2025/CHS/Revit-API/files/Revit_API_Developers_Guide/Introduction/Revit_API_Revit_API_Developers_Guide_Introduction_Add_In_Integration_html.html
- Revit add-in registration: https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API/files/Revit_API_Developers_Guide/Introduction/Add_In_Integration/Revit_API_Revit_API_Developers_Guide_Introduction_Add_In_Integration_Add_in_Registration_html.html
- Revit API SDKs/tools and past versions: https://aps.autodesk.com/developer/overview/revit-api
- AutoCAD managed .NET API: https://help.autodesk.com/cloudhelp/2025/ENU/OARX-DevGuide-Managed/files/GUID-4E1AAFA9-740E-4097-800C-CAED09CDFF12.htm
- AutoCAD API SDKs and past versions: https://aps.autodesk.com/developer/overview/autocad-api
- AutoCAD 2027 official help: https://help.autodesk.com/view/OARX/2027/ENU/

## What this is not
This is not a completed 24-product integration test, not a benchmark of Autodesk's proprietary internal algorithms, and not a claim that GooddayGoodbay already controls Autodesk hosts. The next implementation step is to build separate Revit and AutoCAD adapters and execute their host-driven smoke tests on machines containing the matching software.
