# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida_core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from abc import ABCMeta

import io
try:
    from functools import singledispatch  # Python 3.4+
except ImportError:
    from singledispatch import singledispatch

import six

from aiida.orm.node import Node
from aiida.common.links import LinkType
from aiida.common.lang import override


@singledispatch
def to_aiida_type(value):
    """
    Turns basic Python types (str, int, float, bool) into the corresponding AiiDA types.
    """
    raise TypeError("Cannot convert value of type {} to AiiDA type.".format(type(value)))


class Data(Node):
    """
    This class is base class for all data objects.

    Specifications of the Data class:
    AiiDA Data objects are subclasses of Node and should have

    Multiple inheritance must be suppoted, i.e. Data should have methods for
    querying and be able to inherit other library objects such as ASE for
    structures.

    Architecture note:
    The code plugin is responsible for converting a raw data object produced by
    code to AiiDA standard object format. The data object then validates itself
    according to its method. This is done independently in order to allow
    cross-validation of plugins.
    """
    _source_attributes = ['db_name', 'db_uri', 'uri', 'id', 'version', 'extras', 'source_md5', 'description', 'license']

    # Replace this with a dictionary in each subclass that, given a file
    # extension, returns the corresponding fileformat string.
    #
    # This is used in the self.export() method.
    # By default, if not found here,
    # The fileformat string is assumed to match the extension.
    # Example: {'dat': 'dat_multicolumn'}
    _custom_export_format_replacements = {}

    def __copy__(self):
        """Copying a Data node is not supported, use copy.deepcopy or call Data.clone()."""
        raise NotImplementedError('copying a Data node is not supported, use copy.deepcopy')

    def __deepcopy__(self, memo):
        """
        Create a clone of the Data node by pipiong through to the clone method and return the result.

        :returns: an unstored clone of this Data node
        """
        if self.is_stored:
            raise NotImplementedError('deep copying a stored Data node is not supported, use Data.clone() instead')

        return self.clone()

    def clone(self):
        """
        Create a clone of the Data node.

        :returns: an unstored clone of this Data node
        """
        clone = self.__class__()
        clone.dbnode.dbcomputer = self._dbnode.dbcomputer
        clone.dbnode.type = self._dbnode.type
        clone.label = self.label
        clone.description = self.description

        for key, value in self.iterattrs():
            clone._set_attr(key, value)

        for path in self.get_folder_list():
            clone.add_path(self.get_abs_path(path), path)

        return clone

    @property
    def source(self):
        """
        Gets the dictionary describing the source of Data object. Possible fields:

        * **db_name**: name of the source database.
        * **db_uri**: URI of the source database.
        * **uri**: URI of the object's source. Should be a permanent link.
        * **id**: object's source identifier in the source database.
        * **version**: version of the object's source.
        * **extras**: a dictionary with other fields for source description.
        * **source_md5**: MD5 checksum of object's source.
        * **description**: human-readable free form description of the object's source.
        * **license**: a string with a type of license.

        .. note:: some limitations for setting the data source exist, see ``_validate`` method.

        :return: dictionary describing the source of Data object.
        """
        return self.get_attr('source', None)

    @source.setter
    def source(self, source):
        """
        Sets the dictionary describing the source of Data object.

        :raise KeyError: if dictionary contains unknown field.
        :raise ValueError: if supplied source description is not a dictionary.
        """
        if not isinstance(source, dict):
            raise ValueError("Source must be supplied as a dictionary")
        unknown_attrs = tuple(set(source.keys()) - set(self._source_attributes))
        if unknown_attrs:
            raise KeyError("Unknown source parameters: " "{}".format(", ".join(unknown_attrs)))

        self._set_attr('source', source)

    def set_source(self, source):
        """
        Sets the dictionary describing the source of Data object.
        """
        self.source = source

    @property
    def created_by(self):
        inputs = self.get_inputs(link_type=LinkType.CREATE)
        if inputs:
            return inputs[0]
        else:
            return None

    @override
    def add_link_from(self, src, label=None, link_type=LinkType.UNSPECIFIED):
        from aiida.orm.calculation import Calculation

        if link_type is LinkType.CREATE and \
                        len(self.get_inputs(link_type=LinkType.CREATE)) > 0:
            raise ValueError("At most one CREATE node can enter a data node")

        if not isinstance(src, Calculation):
            raise ValueError("Links entering a data object can only be of type calculation")

        return super(Data, self).add_link_from(src, label, link_type)

    @override
    def _linking_as_output(self, dest, link_type):
        """
        Raise a ValueError if a link from self to dest is not allowed.

        An output of a data can only be a calculation
        """
        from aiida.orm.calculation import Calculation
        if not isinstance(dest, Calculation):
            raise ValueError("The output of a data node can only be a calculation")

        return super(Data, self)._linking_as_output(dest, link_type)

    @override
    def _exportcontent(self, fileformat, main_file_name="", **kwargs):
        """
        Converts a Data node to one (or multiple) files.

        Note: Export plugins should return utf8-encoded **bytes**, which can be
        directly dumped to file.

        :param fileformat: the extension, uniquely specifying the file format.
        :type fileformat: str
        :param main_file_name: (empty by default) Can be used by plugin to
            infer sensible names for additional files, if necessary.  E.g. if the
            main file is '../myplot.gnu', the plugin may decide to store the dat
            file under '../myplot_data.dat'.
        :type main_file_name: str
        :param kwargs: other parameters are passed down to the plugin
        :returns: a tuple of length 2. The first element is the content of the
            otuput file. The second is a dictionary (possibly empty) in the format
            {filename: filecontent} for any additional file that should be produced.
        :rtype: (bytes, dict)
        """
        exporters = self._get_exporters()

        try:
            func = exporters[fileformat]
        except KeyError:
            if len(exporters.keys()) > 0:
                raise ValueError("The format {} is not implemented for {}. "
                                 "Currently implemented are: {}.".format(fileformat, self.__class__.__name__, ",".join(
                                     exporters.keys())))
            else:
                raise ValueError("The format {} is not implemented for {}. "
                                 "No formats are implemented yet.".format(fileformat, self.__class__.__name__))

        return func(main_file_name=main_file_name, **kwargs)

    @override
    def export(self, path, fileformat=None, overwrite=False, **kwargs):
        """
        Save a Data object to a file.

        :param fname: string with file name. Can be an absolute or relative path.
        :param fileformat: kind of format to use for the export. If not present,
            it will try to use the extension of the file name.
        :param overwrite: if set to True, overwrites file found at path. Default=False
        :param kwargs: additional parameters to be passed to the
            _exportcontent method
        :return: the list of files created
        """
        import os

        if not path:
            raise ValueError("Path not recognized")

        if os.path.exists(path) and not overwrite:
            raise OSError("A file was already found at {}".format(path))

        if fileformat is None:
            extension = os.path.splitext(path)[1]
            if extension.startswith(os.path.extsep):
                extension = extension[len(os.path.extsep):]
            if not extension:
                raise ValueError("Cannot recognized the fileformat from the " "extension")

            # Replace the fileformat using the replacements specified in the
            # _custom_export_format_replacements dictionary. If not found there,
            # by default assume the fileformat string is identical to the extension
            fileformat = self._custom_export_format_replacements.get(extension, extension)

        retlist = []

        filetext, extra_files = self._exportcontent(
            fileformat, main_file_name=path, **kwargs)

        if not overwrite:
            for fname in extra_files:
                if os.path.exists(fname):
                    raise OSError("The file {} already exists, stopping.".format(fname))

            if os.path.exists(path):
                raise OSError("The file {} already exists, stopping.".format(path))

        for additional_fname, additional_fcontent in extra_files.items():
            retlist.append(additional_fname)
            with io.open(additional_fname, 'wb', encoding=None) as fhandle:
                fhandle.write(additional_fcontent)  # This is up to each specific plugin
        retlist.append(path)
        with io.open(path, 'wb', encoding=None) as fhandle:
            fhandle.write(filetext)

        return retlist

    def _get_exporters(self):
        """
        Get all implemented export formats.
        The convention is to find all _prepare_... methods.
        Returns a dictionary of method_name: method_function
        """
        # NOTE: To add support for a new format, write a new function called as
        # _prepare_"" with the name of the new format
        exporter_prefix = '_prepare_'
        valid_format_names = self.get_export_formats()
        valid_formats = {k: getattr(self, exporter_prefix + k) for k in valid_format_names}
        return valid_formats

    @classmethod
    def get_export_formats(cls):
        """
        Get the list of valid export format strings

        :return: a list of valid formats
        """
        exporter_prefix = '_prepare_'
        method_names = dir(cls)  # get list of class methods names
        valid_format_names = [i[len(exporter_prefix):] for i in method_names if i.startswith(exporter_prefix)
                             ]  # filter them
        return sorted(valid_format_names)

    def importstring(self, inputstring, fileformat, **kwargs):
        """
        Converts a Data object to other text format.

        :param fileformat: a string (the extension) to describe the file format.
        :returns: a string with the structure description.
        """
        importers = self._get_importers()

        try:
            func = importers[fileformat]
        except KeyError:
            if len(importers.keys()) > 0:
                raise ValueError("The format {} is not implemented for {}. "
                                 "Currently implemented are: {}.".format(fileformat, self.__class__.__name__, ",".join(
                                     importers.keys())))
            else:
                raise ValueError("The format {} is not implemented for {}. "
                                 "No formats are implemented yet.".format(fileformat, self.__class__.__name__))

        # func is bound to self by getattr in _get_importers()
        func(inputstring, **kwargs)

    def importfile(self, fname, fileformat=None):
        """
        Populate a Data object from a file.

        :param fname: string with file name. Can be an absolute or relative path.
        :param fileformat: kind of format to use for the export. If not present,
            it will try to use the extension of the file name.
        """
        if fileformat is None:
            fileformat = fname.split('.')[-1]
        with io.open(fname, 'r', encoding='utf8') as fhandle:  # reads in cwd, if fname is not absolute
            self.importstring(fhandle.read(), fileformat)

    def _get_importers(self):
        """
        Get all implemented import formats.
        The convention is to find all _parse_... methods.
        Returns a list of strings.
        """
        # NOTE: To add support for a new format, write a new function called as
        # _parse_"" with the name of the new format
        importer_prefix = '_parse_'
        method_names = dir(self)  # get list of class methods names
        valid_format_names = [i[len(importer_prefix):] for i in method_names if i.startswith(importer_prefix)
                             ]  # filter them
        valid_formats = {k: getattr(self, importer_prefix + k) for k in valid_format_names}
        return valid_formats

    def convert(self, object_format=None, *args):
        """
        Convert the AiiDA StructureData into another python object

        :param object_format: Specify the output format
        """
        if object_format is None:
            raise ValueError("object_format must be provided")
        if not isinstance(object_format, six.string_types):
            raise ValueError('object_format should be a string')

        converters = self._get_converters()

        try:
            func = converters[object_format]
        except KeyError:
            if len(converters.keys()) > 0:
                raise ValueError("The format {} is not implemented for {}. "
                                 "Currently implemented are: {}.".format(object_format, self.__class__.__name__,
                                                                         ",".join(converters.keys())))
            else:
                raise ValueError("The format {} is not implemented for {}. "
                                 "No formats are implemented yet.".format(object_format, self.__class__.__name__))

        return func(*args)

    def _get_converters(self):
        """
        Get all implemented converter formats.
        The convention is to find all _get_object_... methods.
        Returns a list of strings.
        """
        # NOTE: To add support for a new format, write a new function called as
        # _prepare_"" with the name of the new format
        exporter_prefix = '_get_object_'
        method_names = dir(self)  # get list of class methods names
        valid_format_names = [i[len(exporter_prefix):] for i in method_names if i.startswith(exporter_prefix)
                             ]  # filter them
        valid_formats = {k: getattr(self, exporter_prefix + k) for k in valid_format_names}
        return valid_formats

    def _validate(self):
        """
        Perform validation of the Data object.

        .. note:: validation of data source checks license and requires
            attribution to be provided in field 'description' of source in
            the case of any CC-BY* license. If such requirement is too
            strict, one can remove/comment it out.
        """

        super(Data, self)._validate()

        ## Validation of ``source`` is commented out due to Issue #9
        ## (https://bitbucket.org/epfl_theos/aiida_epfl/issues/9/)
        ##
        ## if self.source is not None and \
        ##    self.source.get('license', None) and \
        ##    self.source['license'].startswith('CC-BY') and \
        ##    self.source.get('description', None) is None:
        ##     raise ValidationError("License of the object ({}) requires "
        ##                           "attribution, while none is given in the "
        ##                           "description".format(self.source['license']))


@six.add_metaclass(ABCMeta)
class BaseType(Data):
    """
    Store a base python type as a AiiDA node in the DB.

    Provide the .value property to get the actual value.
    """

    def __init__(self, *args, **kwargs):
        try:
            getattr(self, '_type')
        except AttributeError:
            raise RuntimeError("Derived class must define the _type class member")

        super(BaseType, self).__init__(**self._create_init_args(*args, **kwargs))

    def set_typevalue(self, typevalue):
        _type, value = typevalue
        self._type = _type
        if value:
            self.value = value
        else:
            self.value = _type()

    @property
    def value(self):
        return self.get_attr('value')

    @value.setter
    def value(self, value):
        self._set_attr('value', self._type(value))

    def __str__(self):
        return self.value.__str__()

    def __repr__(self):
        return self.value.__repr__()

    def __eq__(self, other):
        if isinstance(other, BaseType):
            return self.value == other.value
        else:
            return self.value == other

    def __ne__(self, other):
        if isinstance(other, BaseType):
            return self.value != other.value
        else:
            return self.value != other

    def new(self, value=None):
        return self.__class__(typevalue=(self._type, value))

    def _create_init_args(self, *args, **kwargs):
        if args:
            assert not kwargs, "Cannot have positional arguments and kwargs"
            assert len(args) == 1, \
                "Simple data can only take at most one positional argument"

            kwargs['typevalue'] = (self._type, self._type(args[0]))

        elif 'dbnode' not in kwargs:
            if 'typevalue' in kwargs:
                assert kwargs['typevalue'][0] is self._type
                if kwargs['typevalue'][1] is not None:
                    kwargs['typevalue'] = \
                        (self._type, self._type(kwargs['typevalue'][1]))
            else:
                kwargs['typevalue'] = (self._type, None)

        else:
            assert len(kwargs) == 1, \
                "When specifying dbnode it can be the only kwarg"

        return kwargs
