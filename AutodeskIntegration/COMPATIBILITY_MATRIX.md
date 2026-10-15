# Autodesk API compatibility matrix — official-docs-derived

This matrix identifies the framework family for build planning. It is not proof of binary compatibility and does not replace compiling and loading against the exact release's installed API DLLs.

| Product years | Target framework guidance | Evidence |
|---|---|---|
| Revit 2016 | .NET Framework 4.5 | Autodesk Revit 2016 development requirements |
| Revit 2017–2018 | .NET Framework 4.5.2 / 4.6 (verify exact release requirements) | Autodesk Revit 2018 development requirements |
| Revit 2019 | .NET Framework 4.7 | Autodesk Revit 2019 developer guide |
| Revit 2020–2024 | Use each year's official guide; 2024 explicitly requires .NET Framework 4.8 | Autodesk Revit 2024 development requirements |
| Revit 2025–2026 | .NET 8.0 | Autodesk Revit 2026 development requirements |
| Revit 2027 | .NET 10.0 | Autodesk Revit 2027 official plug-in training |
| AutoCAD 2016 | .NET Framework 4.5 | Autodesk AutoCAD 2022 managed .NET compatibility table |
| AutoCAD 2017–2018 | .NET Framework 4.6 | Autodesk AutoCAD managed .NET compatibility table |
| AutoCAD 2019–2020 | .NET Framework 4.7 | Autodesk AutoCAD managed .NET compatibility table |
| AutoCAD 2021–2024 | .NET Framework 4.8 | Autodesk AutoCAD 2024 application compatibility table |
| AutoCAD 2025–2026 | .NET 8.0 | Autodesk AutoCAD official developer training |
| AutoCAD 2027 | .NET 10.0 | Autodesk AutoCAD 2027 official developer training |

## Source links
- Revit 2016 requirements: https://help.autodesk.com/cloudhelp/2016/ENU/Revit-API/files/GUID-FEF0ED40-8658-4C69-934D-7F83FB5D5B63.htm
- Revit 2018 requirements: https://help.autodesk.com/cloudhelp/2018/ENU/Revit-API/Revit_API_Developers_Guide/Introduction/Getting_Started/Welcome_to_the_Revit_Platform_API/Development_Requirements.html
- Revit 2024 requirements: https://help.autodesk.com/cloudhelp/2024/ENU/Revit-API/files/Revit_API_Developers_Guide/Introduction/Getting_Started/Welcome_to_the_Revit_Platform_API/Revit_API_Revit_API_Developers_Guide_Introduction_Getting_Started_Welcome_to_the_Revit_Platform_API_Development_Requirements_html.html
- Revit 2026 requirements: https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API/files/Revit_API_Developers_Guide/Introduction/Getting_Started/Welcome_to_the_Revit_Platform_API/Revit_API_Revit_API_Developers_Guide_Introduction_Getting_Started_Welcome_to_the_Revit_Platform_API_Development_Requirements_html.html
- Revit 2027 plugin training: https://www.autodesk.com/support/technical/article/caas/tsarticles/ts/7JiiE4UoWHaTjxzuF754mL.html
- AutoCAD managed .NET compatibility: https://help.autodesk.com/cloudhelp/2022/ENU/AutoCAD-Customization/files/GUID-A6C680F2-DE2E-418A-A182-E4884073338A.htm
- AutoCAD 2024 compatibility: https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-Customization/files/GUID-D54B0935-1638-4F97-8B37-1EC3635A1E71.htm
- AutoCAD 2027 plugin training: https://www.autodesk.com/support/technical/article/caas/tsarticles/ts/6kRFCS0mCalWLwAOpP9pNT.html

## Smoke-test source
The sibling projects are read-only API smoke tests. Revit command writes version/document/element-count evidence from IExternalCommand. AutoCAD command GOODDAYSMOKE writes application/drawing/model-space evidence from the managed .NET API. They do not claim to implement AI orchestration, create construction deliverables, or validate the full app. Run only against disposable test projects/drawings.
