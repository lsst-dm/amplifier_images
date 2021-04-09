# This file is part of amplifier_images.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

__all__ = (
    "ImageSection",
    "ImageSectionTransform",
)

from abc import abstractmethod
import dataclasses
from typing import cast, Generic, TypeVar

import numpy as np

from lsst.geom import Box2I, ExtentI


_T = TypeVar("_T")
_U = TypeVar("_U")


class ImageSection(Generic[_T]):
    """An abstract interface that provides access to at least a bounding box,
    and possibly some kind of image data associated with it.

    Notes
    -----
    The primary purpose of `ImageSection` is to make a bounding box behave just
    like an image (which has a bounding box) to higher-level code; this lets
    us define objects with multiple regions like `UntrimmedAmplifier` in a way
    that lets them hold either just bounding boxes or complete images.
    """

    @property
    @abstractmethod
    def bbox(self) -> Box2I:
        """The bounding box for this object (`Box2I`).

        This must not be modified in-place by the caller; at best, this will
        silently do nothing, and at worst, it may corrupt internal state.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def image(self) -> _T:
        """The image payload associated with this object, or `None` if there is
        no image.
        """
        raise NotImplementedError()

    @abstractmethod
    def copy(self) -> ImageSection[_T]:
        """Return a copy of the object that deep-copies all image pixel
        values."""
        raise NotImplementedError()

    def without_image(self) -> ImageSection[None]:
        """Return an `ImageSection` with the same bounding box and no image.

        Parameters
        ----------
        image
            New image.  If `None`, this should be equivalent to calling
            `without_image`.  If this object is of a type that has a size or
            bounding box embedded in it, they should already be consistent with
            ``self.bbox``.

        Returns
        -------
        adapted : `ImageSection`
            An `ImageSection` object with `None` as its image.
        """
        from ._box_only import BoxOnlyImageSection

        return BoxOnlyImageSection(self.bbox)

    def with_new_image(self, image: _U) -> ImageSection[_U]:
        """Return an `ImageSection` with the same bounding box and a different
        image.

        Parameters
        ----------
        image
            New image.  If `None`, this should be equivalent to calling
            `without_image`.  If this object is of a type that has a size or
            bounding box embedded in it, they should already be consistent with
            ``self.bbox``.

        Returns
        -------
        adapted : `ImageSection`
            An `ImageSection` wrapper around the given image.

        Raises
        ------
        TypeError
            Raised if the given image is of a type not recognized by this
            object.  All objects should be able to handle at least their own
            type and `None`.
        ValueError
            Raised if the given image's bounding box is not consistent with
            that of ``self``.
        """
        if image is None:
            return self.without_image()  # type: ignore
        elif image.__module__.startswith("lsst.afw.image"):
            from ._afw import AfwImageLike, AfwImageSection

            img = cast(AfwImageLike, image)
            if self.bbox != img.getBBox():
                raise ValueError(f"New image has bbox {img.getBBox()}, not {self.bbox}.")
            return AfwImageSection(img)  # type: ignore
        elif isinstance(image, np.ndarray):
            from ._numpy import NumPyImageSection

            if self.bbox.getHeight() != image.shape[0] or self.bbox.getWidth() != image.shape[1]:
                raise ValueError(f"Array with shape {image.shape} is inconsistent with box {self.bbox}.")
            return NumPyImageSection(image, self.bbox.getMin())  # type: ignore
        else:
            raise TypeError(f"Image {image} of type {type(image)} not recognized.")

    @abstractmethod
    def make_empty(self, bbox: Box2I) -> ImageSection[_T]:
        """Create an empty image section of the same image type as ``self`` for
        the given bounding box.

        Parameters
        ----------
        bbox : `Box2I`
            Bounding box for the new image.

        Returns
        -------
        empty : `ImageSection`
            An image section object with the same pixel type as ``self`` and
            the given ``bbox``.
        """
        raise NotImplementedError()

    @abstractmethod
    def subimage(self, bbox: Box2I) -> ImageSection[_T]:
        """Return a `ImageSection` that is a subimage view into ``self``.

        Parameters
        ----------
        bbox : `Box2I`
            Bounding box of the subimage.

        Returns
        -------
        subset : `ImageSection`
            An image section object that shares pixels with ``self`` and
            satisfies ``subset.bbox == bbox``.
        """
        raise NotImplementedError()

    @abstractmethod
    def assign(self, other: ImageSection[_T]) -> None:
        """Copy values from another image section to ``self``.

        Parameters
        ----------
        other : `ImageSection`
            Image section to copy values from.  Must satisfy
            ``self.bbox.contains(other.bbox)``.
        """
        raise NotImplementedError()

    @abstractmethod
    def apply_transform(self, transform: ImageSectionTransform, *, allow_view: bool) -> ImageSection[_T]:
        """Apply an `ImageSectionTransform` to ``self``.

        Parameters
        ----------
        allow_view : `bool`,
            If `True` (`False` is default), permit the result to share pixels
            with ``self``; in this case it may even be ``self``.  This is
            disabled by default because a copy is required in the general case
            that flips are necessary, so code that implicitly assumes a view is
            returned probably isn't instrument-generic.

        Returns
        -------
        subset : `ImageSection`
            A transformed image section object.
        """
        raise NotImplementedError()


@dataclasses.dataclass
class ImageSectionTransform:
    """An object that describes how to map a particular `ImageSection` to a
    different coordinate systems.

    Notes
    -----
    `ImageSection` objects can only be flipped or shifted, but only flips
    actually require image pixels to be modified (and only because we assume
    our image classes cannot use negative strides, since `lsst.afw.image`
    classes cannot).

    `ImageSectionTransform` specifies both the exact bounding box the image
    would have after applying the transform (`output_bbox`), and whether flips
    in x and y are needed relative to the current image (`flip_x` and
    `flip_y`).  This mix of absolute and relative information is very
    convenient in practice, but it makes it important to remember that this
    object represents a mapping of a particular image section with a particular
    box to a new coordinate system, not a general mapping between two
    coordinate systems that could (e.g.) be applied to other geometries.
    """

    def __post_init__(self) -> None:
        if self.input_bbox.getSize() != self.output_bbox.getSize():
            raise ValueError(
                f"Input ({self.input_bbox}) and output ({self.output_bbox}) box sizes are inconsistent."
            )

    input_bbox: Box2I
    """The bounding box that the image section is expected to start with
    (`Box2I`).
    """

    output_bbox: Box2I
    """The bounding box the image section will have after this transform is
    applied (`Box2I`).
    """

    flip_x: bool = False
    """Whether the x axis must be inverted to apply this transform (`bool`).
    """

    flip_y: bool = False
    """Whether the y axis must be inverted to apply this transform (`bool`).
    """

    @classmethod
    def make_identity(cls, bbox: Box2I) -> ImageSectionTransform:
        """Construct an identity transform that start and ends with the given
        box and performs no flips.
        """
        return cls(input_bbox=bbox, output_bbox=bbox)

    @property
    def is_identity(self) -> bool:
        """`True` if this transform does nothing; `False` otherwise
        (`bool`)."""
        return not (self.flip_x or self.flip_y) and self.input_bbox == self.output_bbox

    def after(self, other: ImageSectionTransform) -> ImageSectionTransform:
        """Return the transform with the same output target as ``self``,
        starting from the input target of ``other``.

        Parameters
        ----------
        other : `ImageSectionTransform`
            Other transform, to apply first.

        Returns
        -------
        composed : `ImageSectionTransform`
            Composition that represents applying ``other``, then ``self``.
        """
        return ImageSectionTransform(
            other.input_bbox,
            self.output_bbox,
            flip_x=(self.flip_x != other.flip_x),
            flip_y=(self.flip_y != other.flip_y),
        )

    def for_subimage(self, bbox: Box2I) -> ImageSectionTransform:
        """Return the transform that maps a subimage to the same coordinate
        system.

        Parameters
        ----------
        bbox : `Box2I`
            Bounding box of the subimage that the new transform will operate
            on.  Must satisfy ``self.input_bbox.contains(bbox)``.

        Returns
        -------
        subimage_transform : `ImageSectionTransform`
            A transform whose ``input_bbox`` is the given ``bbox`` that maps it
            to the appropriate location within ``self.output_bbox`` and applies
            the same flips.
        """
        # Distances (defined to be positive) between minimum points of both
        # boxes and maximum points of both boxes.
        lower_dist_x, lower_dist_y = bbox.getMin() - self.input_bbox.getMin()
        upper_dist_x, upper_dist_y = self.input_bbox.getMax() - bbox.getMax()
        if self.flip_x:
            lower_dist_x, upper_dist_x = upper_dist_x, lower_dist_x
        if self.flip_y:
            lower_dist_y, upper_dist_y = upper_dist_y, lower_dist_y
        output_bbox = Box2I(
            minimum=self.output_bbox.getMin() + ExtentI(lower_dist_x, lower_dist_y),
            maximum=self.output_bbox.getMax() - ExtentI(upper_dist_x, upper_dist_y),
        )
        return ImageSectionTransform(
            input_bbox=bbox,
            output_bbox=output_bbox,
            flip_x=self.flip_x,
            flip_y=self.flip_y,
        )
