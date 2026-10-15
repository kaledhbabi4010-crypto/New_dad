using System;
using System.IO;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace Goodday.AutodeskSmoke.Revit
{
    [Transaction(TransactionMode.ReadOnly)]
    public sealed class RevitSmokeCommand : IExternalCommand
    {
        public Result Execute(
            ExternalCommandData commandData,
            ref string message,
            ElementSet elements)
        {
            try
            {
                UIApplication uiApp = commandData.Application;
                UIDocument uiDoc = uiApp.ActiveUIDocument;
                if (uiDoc == null || uiDoc.Document == null)
                {
                    message = "Open a disposable test project before running GOODDAY_REVIT_SMOKE.";
                    return Result.Failed;
                }

                Document doc = uiDoc.Document;
                int nonTypeElementCount =
                    new FilteredElementCollector(doc)
                        .WhereElementIsNotElementType()
                        .GetElementCount();

                string folder = Path.Combine(
                    Path.GetTempPath(), "GooddayAutodeskSmoke");
                Directory.CreateDirectory(folder);

                string version = SafeFilePart(uiApp.Application.VersionNumber);
                string file = Path.Combine(
                    folder,
                    "revit-" + version + "-" +
                    DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffZ") + ".txt");

                string[] lines = new[]
                {
                    "product=Revit",
                    "version_number=" + uiApp.Application.VersionNumber,
                    "version_name=" + uiApp.Application.VersionName,
                    "version_build=" + uiApp.Application.VersionBuild,
                    "document_title=" + doc.Title,
                    "document_path=" + doc.PathName,
                    "active_view=" + (doc.ActiveView == null ? "" : doc.ActiveView.Name),
                    "non_type_element_count=" + nonTypeElementCount,
                    "document_is_modified=" + doc.IsModified,
                    "test_kind=READ_ONLY_API_SMOKE",
                    "model_mutated=false",
                    "timestamp_utc=" + DateTime.UtcNow.ToString("o")
                };
                File.WriteAllLines(file, lines);
                TaskDialog.Show("Goodday Revit Smoke Test",
                    "Read-only Revit API smoke test completed.\nEvidence: " + file);
                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.ToString();
                return Result.Failed;
            }
        }

        private static string SafeFilePart(string value)
        {
            foreach (char invalid in Path.GetInvalidFileNameChars())
                value = value.Replace(invalid, '_');
            return value;
        }
    }
}
