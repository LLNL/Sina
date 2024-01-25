"""
Groups utility functions needed to post-process Records.

An arbitrary number can be specified on Record ingest, allowing users to
mix-and-match Sina provided post processing (like filtering) without having
an ever-expanding list of kwargs spread across the ingest methods.
"""
import copy
import functools
import math
import numbers


# The mimetype to use for _register_source()
SINA_MIMETYPE = "application/sina"


def _filter_keep(filter_record, preserve_toplevel, target_record):
    """
    Implementation logic for allow_only.

    :param filter_record: A Record with entries that should be kept. Their values don't matter.
    :param preserve_toplevel: Whether to preserve categories like data, files, etc. Their contents
                              can be removed, but the structures will remain. Note that the first
                              level of library_data (the names of libraries) is also counted as
                              toplevel.
    :param target_record: A Record with entries that need to be filtered.
    """
    return_dict = copy.deepcopy(target_record.raw)

    def _recurse_allow(input_subdict, filter_subdict, return_subdict,
                       is_toplevel, was_librarydata):
        for key, val in input_subdict.items():
            if is_toplevel and preserve_toplevel:
                if key not in filter_subdict:
                    return_subdict[key] = {}
                elif isinstance(val, dict):
                    _recurse_allow(input_subdict[key], filter_subdict[key],
                                   return_subdict[key],
                                   key == "library_data" or was_librarydata,
                                   key == "library_data")
                continue
            if key not in filter_subdict:
                del return_subdict[key]
            elif isinstance(val, dict):
                # A bit of logistical cruft here. Librarydata has a layer of names
                # after it, and then each of those names has a toplevel. So we
                # have to do some switcharoo to "skip" one level of toplevel-ness
                is_toplevel = False
                if was_librarydata:
                    is_toplevel = True
                    was_librarydata = False
                elif key == "library_data":
                    was_librarydata = True
                    is_toplevel = True
                _recurse_allow(input_subdict[key], filter_subdict[key],
                               return_subdict[key], is_toplevel, was_librarydata)
    _recurse_allow(target_record.raw, filter_record.raw, return_dict, True, False)
    target_record.raw = return_dict
    return target_record


def _filter_remove(filter_record, preserve_toplevel, target_record):
    """
    Implementation logic for filter_remove.

    :param filter_record: A Record with entries that should be kept. Their values don't matter.
    :param preserve_toplevel: Whether to preserve categories like data, files, etc. Their contents
                              can be removed, but the structures will remain. Note that the first
                              level of library_data (the names of libraries) is also counted as
                              toplevel.
    :param target_record: A Record with entries that need to be filtered.
    """
    return_dict = copy.deepcopy(target_record.raw)

    def _recurse_deny(input_subdict, filter_subdict, return_subdict,
                      is_toplevel, was_librarydata):
        for key, val in input_subdict.items():
            if is_toplevel and preserve_toplevel:
                if key in filter_subdict and isinstance(val, dict):
                    _recurse_deny(input_subdict[key], filter_subdict[key],
                                  return_subdict[key],
                                  key == "library_data" or was_librarydata,
                                  key == "library_data")
                continue
            if key in filter_subdict:
                del return_subdict[key]
            elif isinstance(val, dict):
                # Same switcharoo as its allow-only sister
                is_toplevel = False
                if was_librarydata:
                    is_toplevel = True
                    was_librarydata = False
                elif key == "library_data":
                    was_librarydata = True
                    is_toplevel = True
                if is_toplevel:
                    _recurse_deny(input_subdict[key], filter_subdict[key],
                                  return_subdict[key], is_toplevel, was_librarydata)
    _recurse_deny(target_record.raw, filter_record.raw, return_dict, True, False)
    target_record.raw = return_dict
    return target_record


def _register_source(source, target_record):
    """
    Implementation logic for register_source.

    :param source: The URL to add to the record.
    """
    target_record.add_file(source, mimetype=SINA_MIMETYPE, tags=["sina_json_source_path"])
    return target_record


def _recurse_update(to_update, update_with):
    """Helper, recursively updates dictionaries."""
    for key, val in update_with.items():
        if isinstance(val, dict):
            to_update[key] = _recurse_update(to_update.get(key, {}), val)
        else:
            to_update[key] = val
    return to_update


def _overlay(overlay_record, record_to_be_overlaid):
    """Implementation logic for overlay."""
    updated_raw = _recurse_update(record_to_be_overlaid.raw, overlay_record.raw)
    record_to_be_overlaid.raw = updated_raw
    return record_to_be_overlaid


def _underlay(underlay_record, record_to_be_underlaid):
    """Implementation logic for overlay."""
    updated_raw = _recurse_update(underlay_record.raw, record_to_be_underlaid.raw)
    record_to_be_underlaid.raw = updated_raw
    return record_to_be_underlaid


def _resample_scalar_lists(target_length, affect_with_length, target_record):
    """
    Implementation logic for resample_scalar_lists.

    :param target_length: The length to force-set to.
    :param affect_with_length: The DataRange (if any) describing the length of
                               lists to target.
    :param target_record: The record to affect.
    """
    def _recurse_resample(input_subdict):
        for key, val in input_subdict.items():
            if (isinstance(val, list) and isinstance(val[0], numbers.Real) and
                    (affect_with_length is None or len(val) in affect_with_length)):
                input_subdict[key] = _force_list_to_len(val, target_length)
            elif isinstance(val, dict):
                _recurse_resample(input_subdict[key])
    _recurse_resample(target_record.raw)
    return target_record


def _force_list_to_len(target_list, target_len):
    """
    Helper for resampling method; handles the resample logic.

    It works in three stages:
    1. If the target length is greater than the current length, the list will be
    resized by assigning interim values along the distance between
    (ex, [2, 8] -> [2, 5, 8] or [2, 8] -> [2, 4, 6, 8]).

    2. If current_length % target_length = n, n!=0, n elements will be removed
    spread evenly in increments of current_length/modulo, with any ensuring
    overage being handled by truncation from the end of the target list.

    3. Every nth will be sampled, where n = target_length/current_length.
    By now we know n should be a whole number.

    To help with alignment, the original first and last elements will be restored.

    Suffice to say this is written to be general and deterministic rather than
    statistically rigorous or fast.

    :param target_length: The length to force-set everything to.
    :param target_list: The list to affect.
    """
    # We'll restore the original
    orig_start = target_list[0]
    orig_end = target_list[-1]
    # Pad out the target list if it's less than what we need
    if len(target_list) < target_len:
        # The -1 is to account for the fact that we won't strictly double,
        # as we're doing this linearly and can't do so with the last point.
        upsample = math.ceil(target_len/(len(target_list)-1))
        upsampled = []
        for offset in range(len(target_list)-1):
            # Upsample is the number of samples we'll need to add, so the +1
            # gets us to our actual increment (to avoid the last number we
            # create being equal to offset[n+1])
            distance = (target_list[offset+1] - target_list[offset])/(upsample+1)
            upsamples = [target_list[offset]+distance*sub_offset
                         for sub_offset in range(1, upsample)]
            upsampled.extend([target_list[offset], *upsamples])
        upsampled.append(target_list[-1])
        target_list = upsampled
    # Figure out how far off we are from being able to sample from the target
    # without messy remainders
    correction = len(target_list) % target_len
    # Correct for said remainders
    if correction:
        skip_every = int(len(target_list) / correction)
        del_at = set(x*skip_every for x in range(correction))
        target_list = [target_list[idx] for idx in range(len(target_list)) if idx not in del_at]
        overage = len(target_list) - target_len
        if overage != 0:
            target_list = target_list[:-overage]
        # Goofiness: we restore the original endpoints
        target_list[0] = orig_start
        if len(target_list) > 1:
            target_list[-1] = orig_end
    if len(target_list) > target_len:
        assert len(target_list) % target_len == 0, "Logic error on resample; alert haluska2."
        finished = target_list[::int(len(target_list)/target_len)]
    else:
        assert target_len % len(target_list) == 0, "Logic error on resample; alert haluska2."
        finished = target_list[::int(target_len/len(target_list))]
    finished[0] = orig_start
    finished[-1] = orig_end  # If someone's coercing to len 1, they get the endpoint
    return finished


# These are syntactic sugar methods, provided entirely to avoid users needing
# to use partials or lambdas.
def filter_keep(filter_record, preserve_toplevel=True):
    """
    Given a filter record and target record, keep only entries that appear in the filter record.

    For example, if your target record has entries for "volume" and "mass", and your filter record
    has entries for "volume" and "temperature", then the output would be the intersection of the
    two: a record that only has an entry for "volume". Works for data, curve sets, files, library
    data, etc.

    :param filter_record: A Record with entries that should be kept. Their values don't matter.
    :param preserve_toplevel: Whether to preserve categories like data, files, etc. Their contents
                              can be removed, but the structures will remain. You probably want
                              this to be true; if a category (like curve_sets) is missing from
                              your filter record, it'll simply be emptied out in the target, same
                              for any library_data.
    """
    return functools.partial(_filter_keep, filter_record, preserve_toplevel)


def filter_remove(filter_record, preserve_toplevel=True):
    """
    Given a filter record and target record, remove all entries that appear in the filter record.

    For example, if your target record has entries for "volume" and "mass", and your filter record
    has entries for "volume" and "temperature", then the output would be the set subtraction of the
    latter from the former: a record that only has an entry for "mass". Works for data, curve sets,
    files, library data, etc.

    :param filter_record: A Record with entries that should be removed. Their values don't matter.
    :param preserve_toplevel: Whether to preserve categories like data, files, etc. Their contents
                              can be removed, but the structures will remain. You almost definitely
                              want this to be true, as otherwise specifying data["volume"] in the
                              filter Record will remove ALL data, since "data" is then seen
                              as subtracted (this similarly "protects" the names of libraries in
                              library_data, but not their contents)
    """
    return functools.partial(_filter_remove, filter_record, preserve_toplevel)


def register_source(source):
    """
    Registers the source of a JSON using an internal mimetype.

    :param source: The URL to add to the record.
    """
    return functools.partial(_register_source, source)


def overlay(overlay_record):
    """
    Overlays the contents of some record over another.

    Information in the overlay record not present in the target will be added;
    shared information will be overwritten. Information in the target not in
    the overlay will remain unaltered.

    :param overlay_record: The record to overlay atop another.
    """
    return functools.partial(_overlay, overlay_record)


def underlay(underlay_record):
    """
    Underlays the contents of some record beneath another.

    Information in the underlay record not present in the target will be added;
    shared information will not be altered. Information in the target not in
    the underlay will also be unaltered.

    :param underlay_record: The record to underlay beneath another.
    """
    return functools.partial(_underlay, underlay_record)


def resample_scalar_lists(target_length, affect_with_length=None):
    """
    Finds every/matching scalar list in a record and upsamples/subsamples to a given length.

    Affects both data and curve sets. THIS IS A POTENTIALLY DESTRUCTIVE AND UNCLEVER METHOD
    MEANT FOR LOOKING AT GENERAL BEHAVIOR! It was written for the case of correcting
    overlong/mismatched run lengths in test runs. You may favor more statistically
    rigorous approaches for production data.

    See _force_list_to_len() for implementation notes.

    :param target_length: The length to force-set everything to.
    :param affect_with_length: Takes a Sina DataRange. If provided, will only affect
                               scalar lists whose lengths fall within the specified range.
                               For example, a DataRange(min=2000, min_inclusive=False)
                               with a target_length of 2000 would take any list with a
                               length over 2000 and downsample it to 2000.
    """
    return functools.partial(_resample_scalar_lists, target_length, affect_with_length)
