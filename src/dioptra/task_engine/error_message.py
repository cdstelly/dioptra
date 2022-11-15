"""
Try to derive better error messages for jsonschema validation errors.
"""

from typing import (
    Any, cast, Iterable, MutableMapping, MutableSequence, Sequence, Union
)

import collections
import jsonschema
import jsonschema.exceptions
import jsonschema.protocols
import jsonschema.validators


# Controls indentation of sub-parts of error messages
_INDENT_SIZE = 4


def _indent_lines(lines: MutableSequence[str]) -> MutableSequence[str]:
    """
    Add a level of indentation to each of the given lines.  The given
    line sequence is modified in-place, and for convenience also returned.

    :param lines: A mutable sequence of line strings
    :return: The same sequence object as was passed in, but containing indented
        lines.
    """
    for i, line in enumerate(lines):
        lines[i] = " "*_INDENT_SIZE + line

    return lines


def _json_path_to_string(path: Iterable[Any]) -> str:
    """
    Create a string representation of a JSON path as is used in jsonschema
    ValidationError objects.  For now, a filesystem-like syntax is used with
    slash-delimited strings, which I think winds up being the same as
    JSON-Pointer syntax (rfc6901).

    :param path: A "path" into a JSON structure, as an iterable of values
        (probably strings and ints).
    :return: A string representation of the path
    """
    # Use a filesystem-like syntax?
    return "/" + "/".join(str(elt) for elt in path)


def _schema_reference_to_path(ref: str) -> list[str]:
    """
    Convert a JSON-Schema reference to the same sort of path structure used in
    jsonschema ValidationError objects to identify locations in JSON.  This
    makes programmatically "following" the path to find what it refers to,
    much easier.  The general path structure is a list of strings/ints.  This
    implementation returns a list of strings and does not try to convert any
    path components to any other type.  Absent context, all-digits path
    components are ambiguous (keys or list indices?), so we mustn't change them.

    :param ref: A reference value, as a fragment: "#" followed by a
        JSON-Pointer value.  If the fragment is "#" by itself, return an empty
        list.
    :return: A path as a list of strings
    """

    if ref == "#":
        # I think "#" is legal, and refers to the whole document.
        ref_schema_path = []

    else:
        # Else, assume references start with "#/", i.e. are URL fragments
        # containing JSON pointers which start with "/".
        ref = ref[2:]  # strip the "#/"
        ref_schema_path = ref.split("/")

    return ref_schema_path


def _instance_path_to_description(
    instance_path: Sequence[Union[int, str]]
) -> str:
    """
    Create a nice description of the location in an experiment description
    pointed to by instance_path.  This implementation is crafted specifically
    to the structure of a declarative experiment description.

    :param instance_path: A path, as a list of strings/ints.
    :return: A string description
    """

    path_len = len(instance_path)

    message_parts = []
    if path_len == 0:
        message_parts.append("root level of experiment description")

    else:

        if instance_path[0] == "parameters":
            if path_len == 1:
                message_parts.append("global parameters section")
            else:
                message_parts.append("parameter")

                # Should be a string naming a parameter if parameters were
                # given as a mapping, or an integer index if parameters were
                # given as a list of names.
                parameter_id = instance_path[1]

                if isinstance(parameter_id, str):
                    message_parts.append('"{}"'.format(parameter_id))
                elif isinstance(parameter_id, int):
                    message_parts.append("#" + str(parameter_id+1))

        elif instance_path[0] == "tasks":
            if path_len == 1:
                message_parts.append("tasks section")
            else:
                message_parts.append(
                    'task plugin "' + str(instance_path[1]) + '"'
                )
                if len(instance_path) > 2:
                    if instance_path[2] == "outputs":
                        message_parts.append("outputs")
                    elif instance_path[2] == "plugin":
                        message_parts.append("plugin ID")

        elif instance_path[0] == "graph":
            if path_len == 1:
                message_parts.append("graph section")
            else:
                message_parts.append('step "' + str(instance_path[1]) + '"')
                if len(instance_path) > 2 \
                        and instance_path[2] == "dependencies":
                    message_parts.append("dependencies")

    if message_parts:
        description = " ".join(message_parts)
    else:
        # fallbacks if we don't know another way of describing the location
        instance_path_str = _json_path_to_string(instance_path)
        description = "experiment description location " + instance_path_str

    return description


def _extract_schema_by_schema_path(
    schema_path: Iterable[Union[int, str]],
    full_schema: dict[str, Any],
    schema: Union[dict[str, Any], list[Any]] = None
) -> Union[dict[str, Any], list[Any]]:
    """
    Find the schema sub-document referred to by a path.  The path must not
    include any "$ref" elements; references are transparently dereferenced as
    they are encountered.

    :param schema_path: A path relative to "schema" (or if it is None, then
        relative to "full_schema"), as an iterable of strings/ints.
    :param full_schema: The full schema we are looking inside of.  This is used
        when traversing references, which are always absolute and therefore
        require restarting traversal from the top of the full schema.
    :param schema: The sub-part of full_schema being examined, or None.  If
        None, examine full_schema.
    :return: The sub-part of schema referred to by the given path
    """

    if schema is None:
        schema = full_schema

    if isinstance(schema, dict) and "$ref" in schema:

        # jsonschema's schema paths don't actually contain "$ref" as an
        # element.  The paths pass through as if the referent was substituted
        # for the reference, and the reference wasn't even there.

        # the cast here is necessary: _schema_reference_to_path() is defined
        # to return list[str].  It never returns anything else, so I think it
        # would be incorrect to define it otherwise.  Mypy regards lists as
        # "invariant", i.e. list[A] and list[B] are considered incompatible
        # types no matter the relationship between A and B.  It is effectively
        # forcing the caller to never add anything other than strings to a
        # list[str] since that's what the called function is declared to
        # return.  In this case, the function may return me a list[str], but I
        # know I will be sole owner of it, and so I should be able to do
        # whatever I want with it, including adding values which are not
        # strings, and use it in contexts where non-string content is expected
        # (ints, in this case).
        ref_schema_path: MutableSequence[Union[int, str]] = cast(
            MutableSequence[Union[int, str]],
            _schema_reference_to_path(schema["$ref"])
        )
        # Here, schema_path may have integer list indices.  That's okay.
        ref_schema_path.extend(schema_path)

        result_schema = _extract_schema_by_schema_path(
            ref_schema_path, full_schema
        )

    else:

        schema_path_it = iter(schema_path)
        next_path_component = next(schema_path_it, None)

        if not next_path_component:
            result_schema = schema

        else:

            if isinstance(schema, list):
                # If current schema is a list, this path step must be
                # interpretable as an integer.  We won't actually know whether
                # a given path step which is a string comprised of all digits
                # refers to an all-digits property name, or a list index, until
                # this point.  This ambiguity occurs when splitting a JSON
                # pointer string to obtain a schema path.
                next_path_component = int(next_path_component)

            # next_path_component is correctly inferred to be Union[int, str],
            # but mypy does not consider that a valid index type.  Since
            # 'schema' can have different values at runtime (sometimes lists,
            # sometimes dicts), the below indexing can't always mean the same
            # thing: sometimes it's a key lookup in a dict, sometimes an index
            # lookup in a list.  As a static type checker, mypy seems to want
            # one meaning, and I couldn't figure out how to make that pass mypy
            # checks.
            subschema = schema[next_path_component]  # type: ignore

            result_schema = _extract_schema_by_schema_path(
                schema_path_it, full_schema, subschema
            )

    return result_schema


def _extract_schema_by_reference(
    ref: str, schema: dict[str, Any]
) -> Union[dict[str, Any], list[Any]]:
    """
    Extract a sub-part of the given schema, according to the given reference.

    :param ref: A JSON-Schema reference, starting with "#"
    :param schema: A schema
    :return: A sub-part of the schema
    """
    ref_schema_path = _schema_reference_to_path(ref)
    return _extract_schema_by_schema_path(ref_schema_path, schema)


def _get_one_of_alternative_names(
    alternative_schemas: Iterable[Any],
    full_schema: dict[str, Any]
) -> list[str]:
    """
    Find names for the given alternative schemas.  The names are derived from
    "title" properties of the schemas.  Numeric suffixes may be introduced if
    necessary, to make them unique.

    :param alternative_schemas: An iterable of sub-schemas, relative to
        full_schema
    :param full_schema: The full schema, of which the alternatives are a part.
        Important for being able to resolve references.
    :return: A list of names
    """

    # It is possible, though unlikely, that more than one alternative has the
    # same name (title).  We will add a numeric counter suffix as necessary to
    # force alternative names to be unique.
    name_counts: MutableMapping[str, int] = collections.defaultdict(int)
    names = []

    for idx, alternative_schema in enumerate(alternative_schemas):
        if isinstance(alternative_schema, dict):

            # dereference if it's just a "$ref" schema
            alternative_schema = _extract_schema_by_schema_path(
                [], full_schema, alternative_schema
            )

            name = alternative_schema.get("title")
            if not name:
                name = "Alternative #" + str(idx+1)

        else:
            # rare case... would only apply to true/false schemas I think.
            name = "Alternative #" + str(idx+1)

        # uniquefy names, just in case...
        name_count = name_counts[name]
        name_counts[name] += 1
        if name_count == 0:
            names.append(name)
        else:
            names.append("{}({})".format(name, name_count+1))

    return names


def _is_valid_for_sub_schema(
    full_schema: dict[str, Any],
    sub_schema: dict[str, Any],
    sub_instance: Any
) -> bool:
    """
    Run a validation of document sub_instance against sub_schema.

    :param full_schema: The full schema, of which sub_schema is a part.
        Important for being able to resolve references.
    :param sub_schema: The schema to use for validation
    :param sub_instance: The instance document to validate
    :return: True if sub_instance is valid; False if not
    """
    validator_class = jsonschema.validators.validator_for(full_schema)

    # Without this type annotation, the is_valid() call below is treated as
    # returning Any, and mypy errors since this function is defined to return
    # bool!  Even with the jsonschema type stubs, mypy gets confused.
    validator: jsonschema.protocols.Validator = validator_class(
        schema=sub_schema,
        # Need to construct a resolver from the full schema, since the
        # sub-schema might contain references relative to the full schema,
        # and we need to be able to resolve them.
        resolver=jsonschema.validators.RefResolver.from_schema(
            full_schema
        )
    )

    return validator.is_valid(sub_instance)


def _one_of_too_many_alternatives_satisfied_message_lines(
    error: jsonschema.exceptions.ValidationError,
    schema: dict[str, Any]
) -> list[str]:
    """
    Create an error message specifically about the situation where too many
    alternatives in a oneOf schema were valid.

    :param error: The ValidationError object representing the aforementioned
        type of error
    :param schema: The schema whose validation failed
    :return: An error message, as a list of lines (strings).  Returning a list
        of lines is convenient for callers, who may want to nest this message
        in another, with indented lines.
    """

    alt_names = _get_one_of_alternative_names(error.validator_value, schema)
    error_desc = "Must be exactly one of: {}".format(
        ", ".join(alt_names)
    )

    satisfied_alt_names = []
    for alt_name, alt_schema in zip(alt_names, error.validator_value):
        # Perform a little "mini" validation to determine which alternatives
        # were satisfied, and describe them in the error message.
        if _is_valid_for_sub_schema(
                schema, alt_schema, error.instance
        ):
            satisfied_alt_names.append(alt_name)

    error_desc += (
        ".  Content satisfied more than one alternative: {}.".format(
            ", ".join(satisfied_alt_names)
        )
    )

    return [error_desc]


def _one_of_no_alternatives_satisfied_message_lines(
    error: jsonschema.exceptions.ValidationError,
    schema: dict[str, Any]
) -> list[str]:
    """
    Create an error message specifically about the situation where none of the
    alternatives in a oneOf schema were valid.

    :param error: The ValidationError object representing the aforementioned
        type of error
    :param schema: The schema whose validation failed
    :return: An error message, as a list of lines (strings).  Returning a list
        of lines is convenient for callers, who may want to nest this message
        in another, with indented lines.
    """

    message_lines = []

    # First error message line describes the error in basic terms.

    alt_names = _get_one_of_alternative_names(error.validator_value, schema)
    basic_desc = (
        "Must be exactly one of: {}; all alternatives failed validation."
    ).format(
        ", ".join(alt_names)
    )

    message_lines.append(basic_desc)

    # Subsequent error lines give additional details about the error: errors
    # associated with each oneOf alternative sub-schema.

    # Maps an alternative name to a list of error objects associated with that
    # alternative.  We organize context errors according to the alternative
    # they apply to.
    errors_by_alt = collections.defaultdict(list)

    one_of_schema_path_len = len(error.absolute_schema_path)

    # required to assure mypy that error.context is non-null.  That is checked
    # before this function is called (in fact it is the exact criteria for the
    # call).  Otherwise, it is treated as a non-iterable Optional type.
    assert error.context
    for ctx_error in error.context:
        # schema paths for errors associated with the alternatives
        # will share a common prefix with the schema path for the
        # "oneOf" error.  The next element after the common portion
        # will be an int which is the index of the alternative.
        error_alt_idx = ctx_error.absolute_schema_path[
            one_of_schema_path_len
        ]

        # Mypy infers Union[str, int] for error_alt_idx and complains that it
        # is not a valid index type.  As explained above, in this context, this
        # index must be an int.
        assert isinstance(error_alt_idx, int)
        errors_by_alt[alt_names[error_alt_idx]].append(ctx_error)

    for alt_name, alt_errors in errors_by_alt.items():
        message_lines.append(
            'Errors associated with alternative "{}":'.format(
                alt_name
            )
        )

        for alt_error in alt_errors:
            sub_message_lines = _validation_error_to_message_lines(
                alt_error, schema
            )
            message_lines.extend(_indent_lines(sub_message_lines))

    return message_lines


def _validation_error_to_message_lines(
    error: jsonschema.exceptions.ValidationError,
    schema: dict[str, Any]
) -> list[str]:
    """
    Create a nice error message for the given error object.

    :param error: A ValidationError object which represents some schema
        validation error
    :param schema: The schema whose validation failed
    :return: An error message, as a list of lines (strings).  Returning a list
        of lines is convenient for callers, who may want to nest this message
        in another, with indented lines.
    """

    # Describe "where" the error occurred
    location_desc = _instance_path_to_description(error.absolute_path)

    # Describe "what" error(s) occurred
    if error.validator == "oneOf":

        if error.context:
            what_lines = _one_of_no_alternatives_satisfied_message_lines(
                error, schema
            )

        else:
            what_lines = \
                _one_of_too_many_alternatives_satisfied_message_lines(
                    error, schema
                )

    else:
        # fallback if we can't be more clever about our message
        what_lines = [error.message]

    if len(what_lines) == 1:
        message_lines = [
            "In {}: {}".format(
                location_desc, what_lines[0]
            )
        ]

    else:
        message_lines = [
            "In {}:".format(location_desc)
        ]
        message_lines.extend(_indent_lines(what_lines))

    return message_lines


def validation_error_to_message(
    error: jsonschema.exceptions.ValidationError,
    schema: dict[str, Any]
) -> str:
    """
    Create a nice error message for the given error object.

    :param error: A ValidationError object which represents some schema
        validation error
    :param schema: The schema whose validation failed
    :return: An error message as a string
    """

    message_lines = _validation_error_to_message_lines(
        error, schema
    )

    message = "\n".join(message_lines)

    return message


def validation_errors_to_message(
    errors: Iterable[jsonschema.exceptions.ValidationError],
    schema: dict[str, Any]
) -> str:
    """
    Create a nice error message for the given error objects.  This currently
    just creates error messages for each error individually, and then
    concatenates them all together with blank lines in between.

    :param errors: An iterable of ValidationError objects which represent some
        schema validation errors
    :param schema: The schema whose validation failed, as a dict
    :return: An error message as a string.
    """
    messages = [
        validation_error_to_message(error, schema)
        for error in errors
    ]

    combined_message_str = "\n\n".join(messages)

    return combined_message_str
