# Mathematical and Spatial Tracking Utilities
# Pure functions extracted to improve modularity and testability.

MUTUAL_GAZE_MAX_DISTANCE = 600
MUTUAL_GAZE_MAX_VERTICAL = 150

def calculate_iomin(box_a, box_b):
    """
    Calculates Intersection over Minimum Area (IoMin).
    """
    ix1 = max(box_a[0], box_b[0])
    iy1 = max(box_a[1], box_b[1])
    ix2 = min(box_a[2], box_b[2])
    iy2 = min(box_a[3], box_b[3])

    inter_area = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter_area == 0:
        return 0.0

    area_a = max(1, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
    area_b = max(1, (box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))

    return inter_area / min(area_a, area_b)


def is_face_inside_invigilator(face_box, ghost_boxes, threshold=0.4):
    """
    Returns True if a detected peeking face belongs to the invigilator.
    """
    for ghost_box in ghost_boxes:
        gx1, gy1, gx2, gy2 = int(ghost_box[0]), int(ghost_box[1]), \
                               int(ghost_box[2]), int(ghost_box[3])

        gw = gx2 - gx1
        gh = gy2 - gy1
        mx = int(gw * 0.15)
        my = int(gh * 0.15)
        expanded_box = [gx1 - mx, gy1 - my, gx2 + mx, gy2 + my]

        iomin = calculate_iomin(face_box, expanded_box)
        if iomin > threshold:
            return True

    return False


def match_face_to_track(new_box, face_tracks, iou_threshold=0.2):
    """
    Finds an existing face track that matches new_box using standard IoU.
    """
    best_iou = 0.0
    best_face_id = None

    for face_id, track in face_tracks.items():
        tb = track['box']
        ix1 = max(new_box[0], tb[0])
        iy1 = max(new_box[1], tb[1])
        ix2 = min(new_box[2], tb[2])
        iy2 = min(new_box[3], tb[3])
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            continue
        area_new = max(1, (new_box[2]-new_box[0]) * (new_box[3]-new_box[1]))
        area_tb  = max(1, (tb[2]-tb[0]) * (tb[3]-tb[1]))
        iou = inter / (area_new + area_tb - inter)
        if iou > best_iou:
            best_iou = iou
            best_face_id = face_id

    if best_iou >= iou_threshold:
        return best_face_id
    return None


def match_phone_to_track(new_box, phone_tracks, iou_threshold=0.2):
    """
    Finds an existing phone track that matches new_box using standard IoU.
    """
    best_iou = 0.0
    best_phone_id = None
    for phone_id, track in phone_tracks.items():
        tb = track['box']
        ix1 = max(new_box[0], tb[0])
        iy1 = max(new_box[1], tb[1])
        ix2 = min(new_box[2], tb[2])
        iy2 = min(new_box[3], tb[3])
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            continue
        area_new = max(1, (new_box[2]-new_box[0]) * (new_box[3]-new_box[1]))
        area_tb  = max(1, (tb[2]-tb[0]) * (tb[3]-tb[1]))
        iou = inter / (area_new + area_tb - inter)
        if iou > best_iou:
            best_iou = iou
            best_phone_id = phone_id

    if best_iou >= iou_threshold:
        return best_phone_id
    return None


def classify_gaze_direction(face_box, yaw, frame_width):
    """
    Classify rough gaze direction based on yaw constraint.
    """
    cx = (face_box[0] + face_box[2]) // 2
    cy = (face_box[1] + face_box[3]) // 2
    
    looking = 'forward'
    if yaw < -25:
        looking = 'left'
    elif yaw > 25:
        looking = 'right'
        
    return {
        'center_x': cx,
        'center_y': cy,
        'looking': looking,
        'yaw': yaw
    }


def find_mutual_gaze_pairs(gaze_classifications):
    """
    Identifies if two students are looking at each other simultaneously.
    """
    pairs = []
    rights = [g for g in gaze_classifications if g['looking'] == 'right']
    lefts = [g for g in gaze_classifications if g['looking'] == 'left']
    
    for r in rights:
        for l in lefts:
            if r['center_x'] < l['center_x']:
                h_dist = l['center_x'] - r['center_x']
                v_dist = abs(r['center_y'] - l['center_y'])
                
                if h_dist <= MUTUAL_GAZE_MAX_DISTANCE and v_dist <= MUTUAL_GAZE_MAX_VERTICAL:
                    face_a_id = r['face_id']
                    face_b_id = l['face_id']
                    
                    fid1 = min(face_a_id, face_b_id)
                    fid2 = max(face_a_id, face_b_id)
                    
                    pairs.append({
                        'face_a_id': face_a_id,
                        'face_b_id': face_b_id,
                        'pair_key': f"{fid1}_{fid2}"
                    })
    return pairs
