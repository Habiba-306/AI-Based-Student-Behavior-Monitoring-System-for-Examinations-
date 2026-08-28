import unittest
from utils import (
    calculate_iomin,
    is_face_inside_invigilator,
    match_face_to_track,
    classify_gaze_direction,
    find_mutual_gaze_pairs
)

class TestSpatialLogic(unittest.TestCase):
    def test_calculate_iomin_fully_inside(self):
        # Small face box fully inside large invigilator box
        box_face = [50, 50, 100, 100]
        box_invigilator = [0, 0, 200, 200]
        
        # Area of face = 50*50 = 2500
        # Intersection = 2500
        # IoMin = 2500 / 2500 = 1.0
        self.assertAlmostEqual(calculate_iomin(box_face, box_invigilator), 1.0)
        self.assertAlmostEqual(calculate_iomin(box_invigilator, box_face), 1.0) # commutative

    def test_calculate_iomin_disjoint(self):
        box_a = [0, 0, 50, 50]
        box_b = [100, 100, 150, 150]
        self.assertEqual(calculate_iomin(box_a, box_b), 0.0)

    def test_calculate_iomin_partial_overlap(self):
        box_a = [0, 0, 100, 100]    # area = 10000
        box_b = [50, 50, 150, 150]  # area = 10000
        # Intersection = [50, 50, 100, 100] area = 2500
        # IoMin = 2500 / 10000 = 0.25
        self.assertAlmostEqual(calculate_iomin(box_a, box_b), 0.25)

    def test_is_face_inside_invigilator(self):
        ghost_boxes = [[10, 10, 200, 400]]
        face_box_inside = [50, 50, 100, 100]
        face_box_outside = [300, 300, 400, 400]
        
        self.assertTrue(is_face_inside_invigilator(face_box_inside, ghost_boxes))
        self.assertFalse(is_face_inside_invigilator(face_box_outside, ghost_boxes))

    def test_match_face_to_track(self):
        face_tracks = {
            1: {'box': [100, 100, 200, 200]},
            2: {'box': [500, 500, 600, 600]}
        }
        
        # Box overlapping heavily with track 1
        new_box_1 = [110, 110, 210, 210]
        self.assertEqual(match_face_to_track(new_box_1, face_tracks), 1)
        
        # Completely disjoint box
        new_box_new = [800, 800, 900, 900]
        self.assertIsNone(match_face_to_track(new_box_new, face_tracks))

    def test_classify_gaze_direction(self):
        face_box = [100, 100, 200, 200]
        
        res_left = classify_gaze_direction(face_box, -30, 1280)
        self.assertEqual(res_left['looking'], 'left')
        
        res_right = classify_gaze_direction(face_box, 30, 1280)
        self.assertEqual(res_right['looking'], 'right')
        
        res_fwd = classify_gaze_direction(face_box, 0, 1280)
        self.assertEqual(res_fwd['looking'], 'forward')

    def test_find_mutual_gaze_pairs(self):
        gaze_classifications = [
            {'face_id': 1, 'looking': 'right', 'center_x': 200, 'center_y': 200},
            {'face_id': 2, 'looking': 'left', 'center_x': 400, 'center_y': 200}, # Looking at face 1
            {'face_id': 3, 'looking': 'left', 'center_x': 900, 'center_y': 200}, # Too far horizontally
        ]
        
        pairs = find_mutual_gaze_pairs(gaze_classifications)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]['face_a_id'], 1)
        self.assertEqual(pairs[0]['face_b_id'], 2)
        self.assertEqual(pairs[0]['pair_key'], "1_2")

if __name__ == '__main__':
    unittest.main()
