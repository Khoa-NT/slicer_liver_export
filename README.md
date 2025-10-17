# Slicer Liver Export

Code for my blog post.

![Liver mask](./assets/SlicerCapture.gif)


## Export the segmentation files in Totalsegmentor
Export the nii.gz segmentation files in Totalsegmentor into 3D models (STL, OBJ, PLY)

1. Download the [Totalsegmentor](https://github.com/wasserth/TotalSegmentator) CT dataset from [here](https://zenodo.org/records/10047292) and extract the dataset to your preferred location.
2. Open the [export_from_Slicer.py script](./export_from_Slicer.py) and modify the following variables:
    - `TotalSegmentor_path`: The path to the Totalsegmentor dataset
    - `export_path`: The path to the export directory
    - `selected_segment`: The selected segment to export
    - `export_type`: The type of export {obj, stl, ply}
    - `skip_image_id`: The list of image ids to skip due to some error files that 3DSlicer can't load
3. Open the 3DSlicer and navigate to python console: View > Python console
4. Run the script by pressing Ctrl + g (or Cmd + g on macOS) and select the [export_from_Slicer.py script](./export_from_Slicer.py)
5. The 3D models will be saved to the export directory