using System;
using System.IO;
using System.Linq;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

namespace Goodday.AutodeskSmoke.AutoCAD
{
    public sealed class AutoCADSmokeCommands
    {
        [CommandMethod("GOODDAYSMOKE", CommandFlags.Modal)]
        public void RunReadOnlySmokeTest()
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null)
                throw new InvalidOperationException("Open a disposable test drawing first.");

            int modelSpaceEntityCount;
            using (Transaction tx = doc.Database.TransactionManager.StartTransaction())
            {
                BlockTable bt = (BlockTable)tx.GetObject(
                    doc.Database.BlockTableId, OpenMode.ForRead);
                BlockTableRecord modelSpace = (BlockTableRecord)tx.GetObject(
                    bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);
                modelSpaceEntityCount = modelSpace.Cast<ObjectId>().Count();
                // Read-only: no database object is opened for write and no changes are made.
            }

            string folder = Path.Combine(
                Path.GetTempPath(), "GooddayAutodeskSmoke");
            Directory.CreateDirectory(folder);
            string file = Path.Combine(
                folder,
                "autocad-" + DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffZ") + ".txt");

            string[] lines = new[]
            {
                "product=AutoCAD",
                "application_version=" + Application.Version,
                "drawing_name=" + doc.Name,
                "model_space_entity_count=" + modelSpaceEntityCount,
                "test_kind=READ_ONLY_API_SMOKE",
                "drawing_mutated=false",
                "timestamp_utc=" + DateTime.UtcNow.ToString("o")
            };
            File.WriteAllLines(file, lines);
            doc.Editor.WriteMessage(
                "\nGoodday AutoCAD read-only API smoke test completed. Evidence: " + file);
        }
    }
}
