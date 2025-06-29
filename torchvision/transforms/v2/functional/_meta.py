from typing import Optional

import PIL.Image
import torch
from torchvision import tv_tensors
from torchvision.transforms import _functional_pil as _FP
from torchvision.tv_tensors import BoundingBoxFormat

from torchvision.utils import _log_api_usage_once

from ._utils import _get_kernel, _register_kernel_internal, is_pure_tensor


def get_dimensions(inpt: torch.Tensor) -> list[int]:
    if torch.jit.is_scripting():
        return get_dimensions_image(inpt)

    _log_api_usage_once(get_dimensions)

    kernel = _get_kernel(get_dimensions, type(inpt))
    return kernel(inpt)


@_register_kernel_internal(get_dimensions, torch.Tensor)
@_register_kernel_internal(get_dimensions, tv_tensors.Image, tv_tensor_wrapper=False)
def get_dimensions_image(image: torch.Tensor) -> list[int]:
    chw = list(image.shape[-3:])
    ndims = len(chw)
    if ndims == 3:
        return chw
    elif ndims == 2:
        chw.insert(0, 1)
        return chw
    else:
        raise TypeError(f"Input tensor should have at least two dimensions, but got {ndims}")


_get_dimensions_image_pil = _register_kernel_internal(get_dimensions, PIL.Image.Image)(_FP.get_dimensions)


@_register_kernel_internal(get_dimensions, tv_tensors.Video, tv_tensor_wrapper=False)
def get_dimensions_video(video: torch.Tensor) -> list[int]:
    return get_dimensions_image(video)


def get_num_channels(inpt: torch.Tensor) -> int:
    if torch.jit.is_scripting():
        return get_num_channels_image(inpt)

    _log_api_usage_once(get_num_channels)

    kernel = _get_kernel(get_num_channels, type(inpt))
    return kernel(inpt)


@_register_kernel_internal(get_num_channels, torch.Tensor)
@_register_kernel_internal(get_num_channels, tv_tensors.Image, tv_tensor_wrapper=False)
def get_num_channels_image(image: torch.Tensor) -> int:
    chw = image.shape[-3:]
    ndims = len(chw)
    if ndims == 3:
        return chw[0]
    elif ndims == 2:
        return 1
    else:
        raise TypeError(f"Input tensor should have at least two dimensions, but got {ndims}")


_get_num_channels_image_pil = _register_kernel_internal(get_num_channels, PIL.Image.Image)(_FP.get_image_num_channels)


@_register_kernel_internal(get_num_channels, tv_tensors.Video, tv_tensor_wrapper=False)
def get_num_channels_video(video: torch.Tensor) -> int:
    return get_num_channels_image(video)


# We changed the names to ensure it can be used not only for images but also videos. Thus, we just alias it without
# deprecating the old names.
get_image_num_channels = get_num_channels


def get_size(inpt: torch.Tensor) -> list[int]:
    if torch.jit.is_scripting():
        return get_size_image(inpt)

    _log_api_usage_once(get_size)

    kernel = _get_kernel(get_size, type(inpt))
    return kernel(inpt)


@_register_kernel_internal(get_size, torch.Tensor)
@_register_kernel_internal(get_size, tv_tensors.Image, tv_tensor_wrapper=False)
def get_size_image(image: torch.Tensor) -> list[int]:
    hw = list(image.shape[-2:])
    ndims = len(hw)
    if ndims == 2:
        return hw
    else:
        raise TypeError(f"Input tensor should have at least two dimensions, but got {ndims}")


@_register_kernel_internal(get_size, PIL.Image.Image)
def _get_size_image_pil(image: PIL.Image.Image) -> list[int]:
    width, height = _FP.get_image_size(image)
    return [height, width]


@_register_kernel_internal(get_size, tv_tensors.Video, tv_tensor_wrapper=False)
def get_size_video(video: torch.Tensor) -> list[int]:
    return get_size_image(video)


@_register_kernel_internal(get_size, tv_tensors.Mask, tv_tensor_wrapper=False)
def get_size_mask(mask: torch.Tensor) -> list[int]:
    return get_size_image(mask)


@_register_kernel_internal(get_size, tv_tensors.BoundingBoxes, tv_tensor_wrapper=False)
def get_size_bounding_boxes(bounding_box: tv_tensors.BoundingBoxes) -> list[int]:
    return list(bounding_box.canvas_size)


@_register_kernel_internal(get_size, tv_tensors.KeyPoints, tv_tensor_wrapper=False)
def get_size_keypoints(keypoints: tv_tensors.KeyPoints) -> list[int]:
    return list(keypoints.canvas_size)


def get_num_frames(inpt: torch.Tensor) -> int:
    if torch.jit.is_scripting():
        return get_num_frames_video(inpt)

    _log_api_usage_once(get_num_frames)

    kernel = _get_kernel(get_num_frames, type(inpt))
    return kernel(inpt)


@_register_kernel_internal(get_num_frames, torch.Tensor)
@_register_kernel_internal(get_num_frames, tv_tensors.Video, tv_tensor_wrapper=False)
def get_num_frames_video(video: torch.Tensor) -> int:
    return video.shape[-4]


def _xywh_to_xyxy(xywh: torch.Tensor, inplace: bool) -> torch.Tensor:
    xyxy = xywh if inplace else xywh.clone()
    xyxy[..., 2:] += xyxy[..., :2]
    return xyxy


def _xyxy_to_xywh(xyxy: torch.Tensor, inplace: bool) -> torch.Tensor:
    xywh = xyxy if inplace else xyxy.clone()
    xywh[..., 2:] -= xywh[..., :2]
    return xywh


def _cxcywh_to_xyxy(cxcywh: torch.Tensor, inplace: bool) -> torch.Tensor:
    if not inplace:
        cxcywh = cxcywh.clone()

    # Trick to do fast division by 2 and ceil, without casting. It produces the same result as
    # `torchvision.ops._box_convert._box_cxcywh_to_xyxy`.
    half_wh = cxcywh[..., 2:].div(-2, rounding_mode=None if cxcywh.is_floating_point() else "floor").abs_()
    # (cx - width / 2) = x1, same for y1
    cxcywh[..., :2].sub_(half_wh)
    # (x1 + width) = x2, same for y2
    cxcywh[..., 2:].add_(cxcywh[..., :2])

    return cxcywh


def _xyxy_to_cxcywh(xyxy: torch.Tensor, inplace: bool) -> torch.Tensor:
    if not inplace:
        xyxy = xyxy.clone()

    # (x2 - x1) = width, same for height
    xyxy[..., 2:].sub_(xyxy[..., :2])
    # (x1 * 2 + width) / 2 = x1 + width / 2 = x1 + (x2-x1)/2 = (x1 + x2)/2 = cx, same for cy
    xyxy[..., :2].mul_(2).add_(xyxy[..., 2:]).div_(2, rounding_mode=None if xyxy.is_floating_point() else "floor")

    return xyxy


def _xyxy_to_keypoints(bounding_boxes: torch.Tensor) -> torch.Tensor:
    return bounding_boxes[:, [[0, 1], [2, 1], [2, 3], [0, 3]]]


def _xyxyxyxy_to_keypoints(bounding_boxes: torch.Tensor) -> torch.Tensor:
    return bounding_boxes[:, [[0, 1], [2, 3], [4, 5], [6, 7]]]


def _cxcywhr_to_xywhr(cxcywhr: torch.Tensor, inplace: bool) -> torch.Tensor:
    if not inplace:
        cxcywhr = cxcywhr.clone()

    dtype = cxcywhr.dtype
    if not cxcywhr.is_floating_point():
        cxcywhr = cxcywhr.float()

    half_wh = cxcywhr[..., 2:-1].div(-2, rounding_mode=None if cxcywhr.is_floating_point() else "floor").abs_()
    r_rad = cxcywhr[..., 4].mul(torch.pi).div(180.0)
    cos, sin = r_rad.cos(), r_rad.sin()
    # (cx - width / 2 * cos - height / 2 * sin) = x1
    cxcywhr[..., 0].sub_(half_wh[..., 0].mul(cos)).sub_(half_wh[..., 1].mul(sin))
    # (cy + width / 2 * sin - height / 2 * cos) = y1
    cxcywhr[..., 1].add_(half_wh[..., 0].mul(sin)).sub_(half_wh[..., 1].mul(cos))

    return cxcywhr.to(dtype)


def _xywhr_to_cxcywhr(xywhr: torch.Tensor, inplace: bool) -> torch.Tensor:
    if not inplace:
        xywhr = xywhr.clone()

    dtype = xywhr.dtype
    if not xywhr.is_floating_point():
        xywhr = xywhr.float()

    half_wh = xywhr[..., 2:-1].div(-2, rounding_mode=None if xywhr.is_floating_point() else "floor").abs_()
    r_rad = xywhr[..., 4].mul(torch.pi).div(180.0)
    cos, sin = r_rad.cos(), r_rad.sin()
    # (x1 + width / 2 * cos + height / 2 * sin) = cx
    xywhr[..., 0].add_(half_wh[..., 0].mul(cos)).add_(half_wh[..., 1].mul(sin))
    # (y1 - width / 2 * sin + height / 2 * cos) = cy
    xywhr[..., 1].sub_(half_wh[..., 0].mul(sin)).add_(half_wh[..., 1].mul(cos))

    return xywhr.to(dtype)


def _xywhr_to_xyxyxyxy(xywhr: torch.Tensor, inplace: bool) -> torch.Tensor:
    # NOTE: This function cannot modify the input tensor inplace as it requires a dimension change.
    if not inplace:
        xywhr = xywhr.clone()

    dtype = xywhr.dtype
    if not xywhr.is_floating_point():
        xywhr = xywhr.float()

    wh = xywhr[..., 2:-1]
    r_rad = xywhr[..., 4].mul(torch.pi).div(180.0)
    cos, sin = r_rad.cos(), r_rad.sin()
    xywhr = xywhr[..., :2].tile((1, 4))
    # x1 + w * cos = x2
    xywhr[..., 2].add_(wh[..., 0].mul(cos))
    # y1 - w * sin = y2
    xywhr[..., 3].sub_(wh[..., 0].mul(sin))
    # x1 + w * cos + h * sin = x3
    xywhr[..., 4].add_(wh[..., 0].mul(cos).add(wh[..., 1].mul(sin)))
    # y1 - w * sin + h * cos = y3
    xywhr[..., 5].sub_(wh[..., 0].mul(sin).sub(wh[..., 1].mul(cos)))
    # x1 + h * sin = x4
    xywhr[..., 6].add_(wh[..., 1].mul(sin))
    # y1 + h * cos = y4
    xywhr[..., 7].add_(wh[..., 1].mul(cos))
    return xywhr.to(dtype)


def _xyxyxyxy_to_xywhr(xyxyxyxy: torch.Tensor, inplace: bool) -> torch.Tensor:
    # NOTE: This function cannot modify the input tensor inplace as it requires a dimension change.
    if not inplace:
        xyxyxyxy = xyxyxyxy.clone()

    dtype = xyxyxyxy.dtype
    if not xyxyxyxy.is_floating_point():
        xyxyxyxy = xyxyxyxy.float()

    r_rad = torch.atan2(xyxyxyxy[..., 1].sub(xyxyxyxy[..., 3]), xyxyxyxy[..., 2].sub(xyxyxyxy[..., 0]))
    # x1, y1, (x2 - x1), (y2 - y1), (x3 - x2), (y3 - y2) x4, y4
    xyxyxyxy[..., 4:6].sub_(xyxyxyxy[..., 2:4])
    xyxyxyxy[..., 2:4].sub_(xyxyxyxy[..., :2])
    # sqrt((x2 - x1) ** 2 + (y1 - y2) ** 2) = w
    xyxyxyxy[..., 2] = xyxyxyxy[..., 2].pow(2).add(xyxyxyxy[..., 3].pow(2)).sqrt()
    # sqrt((x2 - x3) ** 2 + (y2 - y3) ** 2) = h
    xyxyxyxy[..., 3] = xyxyxyxy[..., 4].pow(2).add(xyxyxyxy[..., 5].pow(2)).sqrt()
    xyxyxyxy[..., 4] = r_rad.div_(torch.pi).mul_(180.0)
    return xyxyxyxy[..., :5].to(dtype)


def _convert_bounding_box_format(
    bounding_boxes: torch.Tensor, old_format: BoundingBoxFormat, new_format: BoundingBoxFormat, inplace: bool = False
) -> torch.Tensor:

    if new_format == old_format:
        return bounding_boxes

    if tv_tensors.is_rotated_bounding_format(old_format) ^ tv_tensors.is_rotated_bounding_format(new_format):
        raise ValueError("Cannot convert between rotated and unrotated bounding boxes.")

    # TODO: Add _xywh_to_cxcywh and _cxcywh_to_xywh to improve performance
    if old_format == BoundingBoxFormat.XYWH:
        bounding_boxes = _xywh_to_xyxy(bounding_boxes, inplace)
    elif old_format == BoundingBoxFormat.CXCYWH:
        bounding_boxes = _cxcywh_to_xyxy(bounding_boxes, inplace)
    elif old_format == BoundingBoxFormat.CXCYWHR:
        bounding_boxes = _cxcywhr_to_xywhr(bounding_boxes, inplace)
    elif old_format == BoundingBoxFormat.XYXYXYXY:
        bounding_boxes = _xyxyxyxy_to_xywhr(bounding_boxes, inplace)

    if new_format == BoundingBoxFormat.XYWH:
        bounding_boxes = _xyxy_to_xywh(bounding_boxes, inplace)
    elif new_format == BoundingBoxFormat.CXCYWH:
        bounding_boxes = _xyxy_to_cxcywh(bounding_boxes, inplace)
    elif new_format == BoundingBoxFormat.CXCYWHR:
        bounding_boxes = _xywhr_to_cxcywhr(bounding_boxes, inplace)
    elif new_format == BoundingBoxFormat.XYXYXYXY:
        bounding_boxes = _xywhr_to_xyxyxyxy(bounding_boxes, inplace)

    return bounding_boxes


def convert_bounding_box_format(
    inpt: torch.Tensor,
    old_format: Optional[BoundingBoxFormat] = None,
    new_format: Optional[BoundingBoxFormat] = None,
    inplace: bool = False,
) -> torch.Tensor:
    """See :func:`~torchvision.transforms.v2.ConvertBoundingBoxFormat` for details."""
    # This being a kernel / functional hybrid, we need an option to pass `old_format` explicitly for pure tensor
    # inputs as well as extract it from `tv_tensors.BoundingBoxes` inputs. However, putting a default value on
    # `old_format` means we also need to put one on `new_format` to have syntactically correct Python. Here we mimic the
    # default error that would be thrown if `new_format` had no default value.
    if new_format is None:
        raise TypeError("convert_bounding_box_format() missing 1 required argument: 'new_format'")

    if not torch.jit.is_scripting():
        _log_api_usage_once(convert_bounding_box_format)

    if isinstance(old_format, str):
        old_format = BoundingBoxFormat[old_format.upper()]
    if isinstance(new_format, str):
        new_format = BoundingBoxFormat[new_format.upper()]

    if torch.jit.is_scripting() or is_pure_tensor(inpt):
        if old_format is None:
            raise ValueError("For pure tensor inputs, `old_format` has to be passed.")
        return _convert_bounding_box_format(inpt, old_format=old_format, new_format=new_format, inplace=inplace)
    elif isinstance(inpt, tv_tensors.BoundingBoxes):
        if old_format is not None:
            raise ValueError("For bounding box tv_tensor inputs, `old_format` must not be passed.")
        output = _convert_bounding_box_format(
            inpt.as_subclass(torch.Tensor), old_format=inpt.format, new_format=new_format, inplace=inplace
        )
        return tv_tensors.wrap(output, like=inpt, format=new_format)
    else:
        raise TypeError(
            f"Input can either be a plain tensor or a bounding box tv_tensor, but got {type(inpt)} instead."
        )


def _clamp_bounding_boxes(
    bounding_boxes: torch.Tensor, format: BoundingBoxFormat, canvas_size: tuple[int, int]
) -> torch.Tensor:
    # TODO: Investigate if it makes sense from a performance perspective to have an implementation for every
    #  BoundingBoxFormat instead of converting back and forth
    in_dtype = bounding_boxes.dtype
    bounding_boxes = bounding_boxes.clone() if bounding_boxes.is_floating_point() else bounding_boxes.float()
    xyxy_boxes = convert_bounding_box_format(
        bounding_boxes, old_format=format, new_format=tv_tensors.BoundingBoxFormat.XYXY, inplace=True
    )
    xyxy_boxes[..., 0::2].clamp_(min=0, max=canvas_size[1])
    xyxy_boxes[..., 1::2].clamp_(min=0, max=canvas_size[0])
    out_boxes = convert_bounding_box_format(
        xyxy_boxes, old_format=BoundingBoxFormat.XYXY, new_format=format, inplace=True
    )
    return out_boxes.to(in_dtype)


def _clamp_rotated_bounding_boxes(
    bounding_boxes: torch.Tensor, format: BoundingBoxFormat, canvas_size: tuple[int, int]
) -> torch.Tensor:
    # TODO: For now we are not clamping rotated bounding boxes.
    in_dtype = bounding_boxes.dtype
    out_boxes = bounding_boxes.clone() if bounding_boxes.is_floating_point() else bounding_boxes.float()

    return out_boxes.to(in_dtype)


def clamp_bounding_boxes(
    inpt: torch.Tensor,
    format: Optional[BoundingBoxFormat] = None,
    canvas_size: Optional[tuple[int, int]] = None,
) -> torch.Tensor:
    """See :func:`~torchvision.transforms.v2.ClampBoundingBoxes` for details."""
    if not torch.jit.is_scripting():
        _log_api_usage_once(clamp_bounding_boxes)

    if torch.jit.is_scripting() or is_pure_tensor(inpt):

        if format is None or canvas_size is None:
            raise ValueError("For pure tensor inputs, `format` and `canvas_size` have to be passed.")
        if tv_tensors.is_rotated_bounding_format(format):
            return _clamp_rotated_bounding_boxes(inpt, format=format, canvas_size=canvas_size)
        else:
            return _clamp_bounding_boxes(inpt, format=format, canvas_size=canvas_size)
    elif isinstance(inpt, tv_tensors.BoundingBoxes):
        if format is not None or canvas_size is not None:
            raise ValueError("For bounding box tv_tensor inputs, `format` and `canvas_size` must not be passed.")
        if tv_tensors.is_rotated_bounding_format(inpt.format):
            output = _clamp_rotated_bounding_boxes(
                inpt.as_subclass(torch.Tensor), format=inpt.format, canvas_size=inpt.canvas_size
            )
        else:
            output = _clamp_bounding_boxes(
                inpt.as_subclass(torch.Tensor), format=inpt.format, canvas_size=inpt.canvas_size
            )
        return tv_tensors.wrap(output, like=inpt)
    else:
        raise TypeError(
            f"Input can either be a plain tensor or a bounding box tv_tensor, but got {type(inpt)} instead."
        )


def _clamp_keypoints(keypoints: torch.Tensor, canvas_size: tuple[int, int]) -> torch.Tensor:
    dtype = keypoints.dtype
    keypoints = keypoints.clone() if keypoints.is_floating_point() else keypoints.float()
    # Note that max is canvas_size[i] - 1 and not can canvas_size[i] like for
    # bounding boxes.
    keypoints[..., 0].clamp_(min=0, max=canvas_size[1] - 1)
    keypoints[..., 1].clamp_(min=0, max=canvas_size[0] - 1)
    return keypoints.to(dtype=dtype)


def clamp_keypoints(
    inpt: torch.Tensor,
    canvas_size: Optional[tuple[int, int]] = None,
) -> torch.Tensor:
    """See :func:`~torchvision.transforms.v2.ClampKeyPoints` for details."""
    if not torch.jit.is_scripting():
        _log_api_usage_once(clamp_keypoints)

    if torch.jit.is_scripting() or is_pure_tensor(inpt):

        if canvas_size is None:
            raise ValueError("For pure tensor inputs, `canvas_size` has to be passed.")
        return _clamp_keypoints(inpt, canvas_size=canvas_size)
    elif isinstance(inpt, tv_tensors.KeyPoints):
        if canvas_size is not None:
            raise ValueError("For keypoints tv_tensor inputs, `canvas_size` must not be passed.")
        output = _clamp_keypoints(inpt.as_subclass(torch.Tensor), canvas_size=inpt.canvas_size)
        return tv_tensors.wrap(output, like=inpt)
    else:
        raise TypeError(f"Input can either be a plain tensor or a keypoints tv_tensor, but got {type(inpt)} instead.")
