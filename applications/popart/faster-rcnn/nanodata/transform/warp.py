# Copyright (c) 2021 Graphcore Ltd. All rights reserved.
# Copyright 2021 RangiLyu.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import math
import random

import cv2
import numpy as np


def get_flip_matrix(prob=0.5):
    F = np.eye(3)
    if random.random() < prob:
        F[0, 0] = -1
    return F


def get_perspective_matrix(perspective=0):
    """

    :param perspective:
    :return:
    """
    P = np.eye(3)
    P[2, 0] = random.uniform(-perspective,
                             perspective)  # x perspective (about y)
    P[2, 1] = random.uniform(-perspective,
                             perspective)  # y perspective (about x)
    return P


def get_rotation_matrix(degree=0):
    """

    :param degree:
    :return:
    """
    R = np.eye(3)
    a = random.uniform(-degree, degree)
    R[:2] = cv2.getRotationMatrix2D(angle=a, center=(0, 0), scale=1)
    return R


def get_scale_matrix(ratio=(1, 1)):
    """

    :param ratio:
    """
    Scl = np.eye(3)
    scale = random.uniform(*ratio)
    Scl[0, 0] *= scale
    Scl[1, 1] *= scale
    return Scl


def get_stretch_matrix(width_ratio=(1, 1), height_ratio=(1, 1)):
    """

    :param width_ratio:
    :param height_ratio:
    """
    Str = np.eye(3)
    Str[0, 0] *= random.uniform(*width_ratio)
    Str[1, 1] *= random.uniform(*height_ratio)
    return Str


def get_shear_matrix(degree):
    """

    :param degree:
    :return:
    """
    Sh = np.eye(3)
    Sh[0, 1] = math.tan(random.uniform(-degree, degree) * math.pi /
                        180)  # x shear (deg)
    Sh[1, 0] = math.tan(random.uniform(-degree, degree) * math.pi /
                        180)  # y shear (deg)
    return Sh


def get_translate_matrix(translate, width, height):
    """

    :param translate: [width_translate, height_translate] or width_and_height
    :return:
    """
    if isinstance(translate, (int, float)):
        translate = [translate, translate]
    elif isinstance(translate, (list, tuple)):
        pass
    else:
        raise NotImplementedError
    T = np.eye(3)
    T[0, 2] = random.uniform(0.5 - translate[0],
                             0.5 + translate[0]) * width  # x translation
    T[1, 2] = random.uniform(0.5 - translate[1],
                             0.5 + translate[1]) * height  # y translation
    return T


def get_resize_matrix(raw_shape, dst_shape, keep_ratio, alignShortSide=False):
    """
    Get resize matrix for resizing raw img to input size
    :param raw_shape: (width, height) of raw image
    :param dst_shape: (width, height) of input image
    :param keep_ratio: whether keep original ratio
    :return: 3x3 Matrix
    """
    r_w, r_h = raw_shape
    d_w, d_h = dst_shape
    Rs = np.eye(3)
    if keep_ratio:
        C = np.eye(3)
        C[0, 2] = -r_w / 2
        C[1, 2] = -r_h / 2

        rate1 = r_w / r_h * -1 if alignShortSide else r_w / r_h
        rate2 = d_w / d_h * -1 if alignShortSide else d_w / d_h
        if rate1 < rate2:
            ratio = d_h / r_h
        else:
            ratio = d_w / r_w
        Rs[0, 0] *= ratio
        Rs[1, 1] *= ratio

        T = np.eye(3)
        T[0, 2] = 0.5 * d_w
        T[1, 2] = 0.5 * d_h
        return T @ Rs @ C
    else:
        Rs[0, 0] *= d_w / r_w
        Rs[1, 1] *= d_h / r_h
        return Rs


def warp_and_resize(meta, warp_kwargs, dst_shape, keep_ratio=True):
    # TODO: background, type
    # dst_shape: [width,height]
    raw_img = meta["img"]
    height = raw_img.shape[0]  # shape(h,w,c)
    width = raw_img.shape[1]

    # center
    C = np.eye(3)
    C[0, 2] = -width / 2
    C[1, 2] = -height / 2

    # do not change the order of mat mul
    # if "perspective" in warp_kwargs and random.randint(0, 1):
    if warp_kwargs.get('perspective', False) and random.randint(0, 1):
        P = get_perspective_matrix(warp_kwargs["perspective"])
        C = P @ C
    # if "scale" in warp_kwargs and random.randint(0, 1):
    if warp_kwargs.get('scale', False) and random.randint(0, 1):
        Scl = get_scale_matrix(warp_kwargs["scale"])
        C = Scl @ C
    # if "stretch" in warp_kwargs and random.randint(0, 1):
    if warp_kwargs.get('stretch', False) and random.randint(0, 1):
        Str = get_stretch_matrix(*warp_kwargs["stretch"])
        C = Str @ C
    # if "rotation" in warp_kwargs and random.randint(0, 1):
    if warp_kwargs.get('rotation', False) and random.randint(0, 1):
        R = get_rotation_matrix(warp_kwargs["rotation"])
        C = R @ C
    # if "shear" in warp_kwargs and random.randint(0, 1):
    if warp_kwargs.get('shear', False) and random.randint(0, 1):
        Sh = get_shear_matrix(warp_kwargs["shear"])
        C = Sh @ C
    # if "flip" in warp_kwargs:
    if warp_kwargs.get('flip', False):
        F = get_flip_matrix(warp_kwargs["flip"])
        C = F @ C
    # if "translate" in warp_kwargs and random.randint(0, 1):
    if warp_kwargs.get('translate', False) and random.randint(0, 1):
        T = get_translate_matrix(warp_kwargs["translate"], width, height)
    else:
        T = get_translate_matrix(0, width, height)
    M = T @ C
    ResizeM = get_resize_matrix((width, height), dst_shape, keep_ratio)
    M = ResizeM @ M
    img = cv2.warpPerspective(raw_img, M, dsize=tuple(dst_shape))
    meta["img"] = img
    meta["warp_matrix"] = M
    if "gt_bboxes" in meta:
        boxes = meta["gt_bboxes"]
        meta["gt_bboxes"] = warp_boxes(boxes, M, dst_shape[0], dst_shape[1])
    if "gt_masks" in meta:
        for i, mask in enumerate(meta["gt_masks"]):
            meta["gt_masks"][i] = cv2.warpPerspective(mask,
                                                      M,
                                                      dsize=tuple(dst_shape))

    # TODO: keypoints
    # if 'gt_keypoints' in meta:

    return meta


def warp_boxes(boxes, M, width, height):
    n = len(boxes)
    if n:
        # warp points
        xy = np.ones((n * 4, 3))
        xy[:, :2] = boxes[:, [0, 1, 2, 3, 0, 3, 2, 1]].reshape(
            n * 4, 2)  # x1y1, x2y2, x1y2, x2y1
        xy = xy @ M.T  # transform
        xy = (xy[:, :2] / xy[:, 2:3]).reshape(n, 8)  # rescale
        # create new boxes
        x = xy[:, [0, 2, 4, 6]]
        y = xy[:, [1, 3, 5, 7]]
        xy = np.concatenate(
            (x.min(1), y.min(1), x.max(1), y.max(1))).reshape(4, n).T
        # clip boxes
        xy[:, [0, 2]] = xy[:, [0, 2]].clip(0, width)
        xy[:, [1, 3]] = xy[:, [1, 3]].clip(0, height)
        return xy.astype(np.float32)
    else:
        return boxes