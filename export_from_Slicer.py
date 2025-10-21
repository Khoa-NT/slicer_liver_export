"""
title: export_from_Slicer.py
date: 2025-10-17 14:41:39
@author: khoa

Convert the nii.gz segmentation files in Totalsegmentor into 3D model (STL, OBJ)

How to use:
    + Open 3DSlicer
    + Open the Python console: View > Python console
    + Click on the Python console and run the script by pressing Ctrl(or Cmd) + g to open the python script
    + The script will be executed and the results will be saved to the export directory
"""
import slicer
import vtk

from typing import Any
from pathlib import Path
import shutil


def export_segmentation(file_path:Path, save_path:Path, writer):
    segmentationNode = slicer.util.loadSegmentation(file_path, properties={"name":file_path.parents[1].name})

    ### Segmentation can only be shown in 3D if closed surface representation (or other 3D-displayable representation) is available.
    ### Return: True or False
    is_ClosedSurface = segmentationNode.CreateClosedSurfaceRepresentation()
    if not is_ClosedSurface:
        return -1
    
    segmentation=segmentationNode.GetSegmentation()

    ### Count the segment
    n_segments = segmentation.GetNumberOfSegments()

    ### If there is no Segmentation in the segmentationNode
    if n_segments == 0:
        return 0

    ### Process View node if used
    if isinstance(writer, (vtk.vtkOBJExporter, vtk.vtkGLTFExporter)):
        ### We have to turn off these when we export based on the scene
        ### Get the ViewNode
        v = slicer.mrmlScene.GetNodeByID('vtkMRMLViewNode1')

        ### Turn off "3D cube" and "3D axis label"
        v.SetAxisLabelsVisible(False)
        v.SetBoxVisible(False)

    ### Loop throught each segment
    for segmentIndex in range(n_segments):
        segmentID = segmentation.GetNthSegmentID(segmentIndex)

        ### Most of the object in 3DSlicer is PolyData
        ### Ref: 5.6 Types of Datasets in book https://gitlab.kitware.com/vtk/textbook/raw/master/VTKBook/VTKTextBook.pdf
        outputPolyData = vtk.vtkPolyData()

        ### Double check again
        is_ClosedSurface = segmentationNode.GetClosedSurfaceRepresentation(segmentID, outputPolyData)
        if not is_ClosedSurface:
            continue
        
        ### Export the segmentation based on the writer type
        if isinstance(writer, vtk.vtkSTLWriter):
            writer.SetInputData(outputPolyData)

            ### E.g., segmentationNode.GetName() = 's0095'
            writer.SetFileName(f"{save_path/segmentationNode.GetName()}_{segmentID}.stl")
        
        elif isinstance(writer, vtk.vtkOBJExporter):
            ### OBJ need render input from render window
            writer.SetRenderWindow(slicer.app.layoutManager().threeDWidget(0).threeDView().renderWindow())

            ### Save the stem (prefixname)
            writer.SetFilePrefix(f"{save_path/segmentationNode.GetName()}_{segmentID}") ### The output will be .obj and .mtl

        elif isinstance(writer, vtk.vtkPLYWriter):
            writer.SetInputData(outputPolyData)
            writer.SetFileName(f"{save_path/segmentationNode.GetName()}_{segmentID}.ply")
            writer.SetFileTypeToBinary() # Write in binary format Or writer.SetFileTypeToASCII() for ASCII format
        else:
            raise ValueError(f"Export type {export_type} is not supported")

        ### Write the segmentation
        writer.Write()

    return n_segments


def create_directory(path:Path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(exist_ok=True, parents=True)


def main(data_path:Path, export_path:Path, selected_segment:str="liver", export_type:str="obj", 
         skip_image_id:list[str]=None, use_pandas:bool=False, debug:bool=False):
    if skip_image_id is None:
        skip_image_id = []

    ### Pick a writer based on the export type
    ### Ref: https://vtk.org/Wiki/VTK_FAQ#What_3D_file_formats_can_VTK_import_and_export?
    export_type = export_type.lower()
    if export_type == "obj":
        writer = vtk.vtkOBJExporter()
    elif export_type == "stl":
        writer = vtk.vtkSTLWriter()
    elif export_type == "ply":
        writer = vtk.vtkPLYWriter()
    elif export_type == "gltf":
        writer = vtk.vtkGLTFExporter()
    else:
        raise ValueError(f"Export type {export_type} is not supported")

    ### Create the export directory
    save_path = export_path / f"{data_path.name}__{selected_segment}__{export_type}"
    create_directory(save_path)
    
    if use_pandas:
        try:
            import pandas as pd
        except ImportError:
            from slicer.util import pip_install
            pip_install("pandas[excel]")
            import pandas as pd
        
        ### Create a dataframe to store the results
        df = pd.DataFrame(columns=["patient_id", "n_segment"])
    else:
        save_log_path = export_path/f"{save_path.name}__log.log"
        f_log = open(save_log_path, "w")

    ### Get the list of patient ids
    patient_ids = sorted([folder.name for folder in data_path.iterdir() if folder.is_dir()])


    ### --------- Iterate through each row --------- ###
    count = 0
    for patient_id in patient_ids:
        ### Skip the patient if it is in the skip_image_id list
        if patient_id in skip_image_id:
            skip_image_id.remove(patient_id)
            if use_pandas:
                df.loc[len(df)] = [patient_id, -2] ### Add a new row with patient_id and -2 (skipped)
            else:
                f_log.write(f"{patient_id} is skipped\n")
            continue
        
        ### Get the segmentation path
        seg_path:Path = data_path / patient_id / "segmentations" / f"{selected_segment}.nii.gz"

        ### Check if the segmentation exists
        if not seg_path.exists():
            print(f"{seg_path} doesn't exist")
            if use_pandas:
                df.loc[len(df)] = [patient_id, 0] ### Add a new row with patient_id and 0 (no segmentation)
            else:
                f_log.write(f"{patient_id} doesn't have segmentation\n")

        ### Export the segmentation
        _status = export_segmentation(seg_path, save_path, writer)

        if use_pandas:
            df.loc[len(df)] = [patient_id, _status] ### Add a new row with patient_id and _status (number of segments or -1 if failed)
        else:
            f_log.write(f"{patient_id} exported {_status} segments\n")

        ### Delete temporary node
        slicer.mrmlScene.Clear()

        count += 1
        if debug and count > 10:
            break


    print(f"Exported {count} patients")
    ### Save the results to an excel file
    if use_pandas:
        save_excel_path = export_path/f"{save_path.name}__log.xlsx"
        df.to_excel(save_excel_path, index=False)
        print(f"Saved excel file to {save_excel_path}")
    else:
        f_log.close()
        print(f"Saved log file to {save_log_path}")


if __name__ == "__main__":
    ### Path to the TotalSegmentor dataset
    TotalSegmentor_path = Path("/Users/khoanguyen-tuan/Local/Data_set/Totalsegmentator_dataset_v201")

    ### Path to the export directory
    export_path = Path("/Users/khoanguyen-tuan/Local/Data_set/test_3DSlicer_export")

    ### Selected segment to export
    selected_segment = "heart" ### {liver, heart, spleen, }

    ### Export type
    export_type = "stl" ### {obj, stl, ply}

    ### Some error files that 3DSlicer can't load
    ### Ref similar case: https://github.com/wasserth/TotalSegmentator/issues/268
    skip_image_id = ['s1406', 's1407', 's1409', 's1417', 's1419']

    main(
        data_path=TotalSegmentor_path, 
        export_path=export_path, 
        export_type=export_type, 
        selected_segment=selected_segment,
        skip_image_id=skip_image_id, 
        use_pandas=False ### If True, the results will be saved to an excel file
    )
    print("Done")
    
    # exit() ### Uncomment this if you want to exit the 3DSlicer after the script is done