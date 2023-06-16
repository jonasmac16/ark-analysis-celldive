


def tile_sizer(img_col_dim, img_row_dim, min_col_tile_size, min_row_tile_size, overlap, max_tile_area = 5000^2, min_tile_area = 500^2, n_tiles = range(2,10)):
    def _f_xy(dim_size, n, tile_size, ov):
        return dim_size <= ov + n * (tile_size - ov)
    
    def _xy_ratio(col_tile_size, row_tile_size):
        if 0 in [col_tile_size, row_tile_size]:
            return True
        return 2.0 >= col_tile_size/row_tile_size >= 0.5
   
    def _max_tile_size(col_dim, row_dim, ref=max_tile_area):
        return col_dim*row_dim < ref
    
    def test_cond(img_col_dim, img_row_dim, col_tile_size,row_tile_size, n, overlap):
        col_tile_size_final = np.minimum(np.maximum(range(0, x+overlap, col_tile_size)[-1] - overlap, 0) + col_tile_size, x) - np.maximum(range(0, x+overlap, col_tile_size)[-1] - overlap, 0)
        row_tile_size_final = np.minimum(np.maximum(range(0, y+overlap, row_tile_size)[-1] - overlap, 0) + row_tile_size, y) - np.maximum(range(0, y+overlap, row_tile_size)[-1] - overlap, 0)
        return(_f_xy(img_row_dim, n, row_tile_size, overlap) and _f_xy(img_col_dim, n, col_tile_size, overlap) and _max_tile_size(col_tile_size, row_tile_size) and _min_tile_size(col_tile_size_final, row_tile_size_final) and _xy_ratio(col_tile_size, row_tile_size) and _xy_ratio(col_tile_size_final, row_tile_size) and _xy_ratio(col_tile_size, row_tile_size_final) and _xy_ratio(col_tile_size_final, row_tile_size_final))
    
    def _min_tile_size(col_dim, row_dim, ref=min_tile_area):
        return col_dim*row_dim >= ref
    
    res = None

    if _max_tile_size(img_col_dim,img_row_dim):
        res = {'col_tile_size' : img_col_dim, 'row_tile_size' : img_row_dim, 'n_tiles' : 1, 'overlap' : 0}
    
    else:    
        for n in n_tiles:
            for col_tile_size in reversed(np.maximum(range(round(x/n), min_col_tile_size), np.minimum((y*2)+1, x+1))):
                for row_tile_size in reversed(np.maximum(range(round(col_tile_size/2), min_row_tile_size), np.minimum(round(col_tile_size*2), y+1))):
                    if test_cond(img_col_dim,img_row_dim,col_tile_size,row_tile_size, n, overlap):
                        res = {'col_tile_size' : col_tile_size, 'row_tile_size' : row_tile_size, 'n_tiles' : n, 'overlap' : overlap}

    if res == None:
        raise ValueError(f"No appropriate tile size for {img.shape} and overlap {overlap} could be determined.")
    else:
        return(res)
    

def remove_boundary_mask(arr, boundary, boundary_sides, dummy_var):
    boundary_ids = list()
    for boundary_side in boundary_sides:
        if "t" in boundary_side:
            boundary_mask = arr[0:boundary, :]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]
            
        elif "b" in boundary_side:
            boundary_mask = arr[-boundary:, :]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]
            
        elif "r" in boundary_side:
            boundary_mask = arr[:, -boundary:]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]

        elif "l" in boundary_side:
            boundary_mask = arr[:, 0:boundary]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]
    
    boundary_ids = np.unique(boundary_ids)
    boundary_ids= [i for i in boundary_ids if i != 0]
    cleaned_arr = np.where(np.isin(arr, boundary_ids), dummy_var, arr)
    return(cleaned_arr)
    

def determine_boundaries(img, r0,r1,c0,c1):
    boundaries = list()
    if c0 != 0:
        boundaries.append("l")
    if c1 != img.shape[2]:
        boundaries.append("r")
    if r0 != 0:
        boundaries.append("t")
    if r1 != img.shape[1]:
        boundaries.append("b")
    
    return(boundaries)

def tiled_segmentation_overlap(img, start_row, start_col, stop_row, stop_col, step_size_row, step_size_col, dummy_var, overlap = 0, cutoff=2, background_threshold = 0.1, compartment='whole-cell'):
    if compartment in ["whole-cell", "nuclear"]:
        mask_array = np.expand_dims(np.full_like(img, -99, dtype=int)[:,:,:,0], 3)
    elif compartment == "both":
        mask_array = np.full_like(img, -99, dtype=int)
    
    max_current_cell_id = np.zeros(mask_array.shape[3]) 
    
    for row in range(start_row, stop_row, step_size_row):
        for col in range(start_col, stop_col, step_size_col):
            r0, r1 = np.maximum(row - overlap, 0), np.minimum(np.maximum(row - overlap, 0) + step_size_row, img.shape[1])
            c0, c1 = np.maximum(col - overlap, 0), np.minimum(np.maximum(col - overlap, 0) + step_size_col, img.shape[2])
                        
            boundaries = determine_boundaries(img, r0,r1,c0,c1)
            
            if np.max(img[:,:,:,:]) < background_threshold:
                tmp_segmentation = np.zeros_like(mask_array, dtype=int)[:, r0:r1, c0:c1,:]
            else:
                tmp_segmentation = app.predict(img[:, r0:r1, c0:c1,:], compartment=compartment)

                for j in range(tmp_segmentation.shape[3]):
                    tmp_segmentation[0,:,:,j] = remove_boundary_mask(tmp_segmentation[0,:,:,j], cutoff, boundaries, dummy_var)

                    tmp_segmentation[0,:,:,j] = make_cell_mask_unique(tmp_segmentation[0,:,:,j], dummy_var, max_current_cell_id[j])
                    max_current_cell_id[j] = np.max(tmp_segmentation[0,:,:,j])
            for j in range(tmp_segmentation.shape[3]):        
                ### remove overlapping ids
                insert_mask = np.isin(mask_array[0, r0:r1, c0:c1, j], dummy_var)
                mask_array[0, r0:r1, c0:c1, j][insert_mask] = tmp_segmentation[0,:,:,j][insert_mask]

    gc.collect()
    return(mask_array)

def getval_array(d):
    # based on https://stackoverflow.com/a/46870227
    v = np.array(list(d.values()))
    k = np.array(list(d.keys()))
    maxv = k.max()
    minv = k.min()
    n = maxv - minv + 1
    val = np.empty(n,dtype=v.dtype)
    val[k] = v
    return val


def make_cell_mask_unique(input_array, dummy_var, offset):
    cell_ids = np.unique(input_array)
    cell_ids = cell_ids[~np.isin(cell_ids, [dummy_var, 0])]
    
    transdict = {cell_ids[n] : n + offset + 1 for n in range(0,cell_ids.shape[0])}
    transdict.update({0 : 0})
    transdict.update({dummy_var : dummy_var})
    
    val_arr = getval_array(transdict)
    out = val_arr[input_array]
    
    return(out)


def _combine_overlapping_masks(mask_x, mask_y, dummy_var):
    max_cell_id_x = np.max(mask_x)

    mask_out_x = make_cell_mask_unique(mask_x, dummy_var, 0)
    mask_out_y = make_cell_mask_unique(mask_y, dummy_var, max_cell_id_x)

    # mask_xy = np.copy(mask_x)
    mask_x[np.isin(mask_out_x, dummy_var)] = mask_out_y[np.isin(mask_out_x, dummy_var)]
    gc.collect()
    return(mask_x)

def predict_tiled(img, min_tile_size_col, min_tile_size_row, dummy_var, overlap=0, cutoff=2, background_threshold= 0.1, infer_gaps = True, compartment='whole-cell'):
    #   ensure the image has 4 dimensions to start with and that the last one is 2 dims
    if len(img.shape) != 4:
        raise ValueError(f"Image data must be 4D, got image of shape {img.shape}")
    if img.shape[3] != 2:
        raise ValueError(f"Each FOV/slide must have 2 channels, the image has {img.shape[3]} channels")
    
    
    #   iterate over the first dimension
    for fov_idx in range(img.shape[0]):
        fov = img[[fov_idx], ...]
        tile = func_tile_sizer_faster(fov.shape[2], fov.shape[1], min_tile_size_col, min_tile_size_row, overlap=overlap)
        
        step_size_row = tile["row_tile_size"]
        step_size_col = tile["col_tile_size"]
        overlap_tiles = tile["overlap"]
        
        print("The tile size chosen is: " + str(step_size_row) +"px X " + str(step_size_col) + "px\nThe overlap is: " + str(overlap_tiles))    

        start_row1, start_col1, stop_row1, stop_col1 = 0, 0, fov.shape[1]+overlap_tiles, fov.shape[2]+overlap_tiles
        
        if infer_gaps:
            _mask = tiled_segmentation_overlap(fov, start_row1, start_col1, stop_row1, stop_col1, step_size_row, step_size_col, dummy_var,overlap = overlap_tiles, cutoff = cutoff, background_threshold = background_threshold, compartment = compartment)
            _mask[np.isin(_mask, [-99])] = 0
        else:
            _mask = tiled_segmentation_overlap(fov, start_row1, start_col1, stop_row1, stop_col1, step_size_row, step_size_col, dummy_var,overlap = 0, cutoff = cutoff, background_threshold = background_threshold, compartment = compartment)
            _mask[np.isin(_mask, [-99])] = 0

        for j in range(_mask.shape[3]):
            _mask[:,:,:,j] = make_cell_mask_unique(_mask[:,:,:,j], -99, 0)
        
        if fov_idx == 0:
            if img.shape[0] == 1:
                return(_mask)
            else:
                mask = np.copy(_mask)
        else:
            mask = np.concatenate([mask, _mask], axis=0)
        
        gc.collect()
        
    return(mask)


def save_model_output_wrapper(segmentation_mask, output_dir, feature_name, compartment):
    save_model_output(segmentation_mask, output_dir=output_dir, feature_name=feature_name)
    # rename saved mask tiff
    old_name = feature_name + '_feature_0_frame_000.tif'
    
    if compartment == "both":
        suffix = ["nuclear", "whole_cell"]
    elif compartment == "whole-cell":
        suffix = "whole_cell"
    elif compartment == "nuclear":
        suffix = "nuclear"
        
    new_name = feature_name + '_' + suffix + '.tiff'
    
    old_name_path = os.path.join(output_dir, old_name)
    new_name_path =  os.path.join(output_dir, new_name)
    os.rename(old_name_path,new_name_path)