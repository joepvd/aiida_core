# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida_core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
"""Implementation of CalcJobNode to add two numbers for testing and demonstration purposes."""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import io

from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.common.exceptions import InputValidationError
from aiida.common.lang import classproperty
from aiida.orm.data.float import Float
from aiida.orm.data.int import Int
from aiida.orm.node.process import CalcJobNode


class ArithmeticAddCalculation(CalcJobNode):
    """Implementation of CalcJobNode to add two numbers for testing and demonstration purposes."""

    # pylint: disable=invalid-name,abstract-method

    def _init_internal_params(self):
        super(ArithmeticAddCalculation, self)._init_internal_params()

        self._PREFIX = 'aiida'  # pylint: disable=invalid-name
        self._INPUT_FILE_NAME = 'aiida.in'
        self._OUTPUT_FILE_NAME = 'aiida.out'

        self._default_parser = 'arithmetic.add'
        self._required_inputs = ['code', 'x', 'y']
        self._optional_inputs = []

        self._DEFAULT_INPUT_FILE = self._INPUT_FILE_NAME
        self._DEFAULT_OUTPUT_FILE = self._OUTPUT_FILE_NAME

    @classproperty
    def _use_methods(cls):
        """
        Define and return the available use_methods
        """
        # pylint: disable=no-self-argument,no-member
        methods = CalcJobNode._use_methods
        methods.update({
            'x': {
                'valid_types': (Int, Float),
                'additional_parameter': None,
                'linkname': 'x',
                'docstring': ('The left operand'),
            },
            'y': {
                'valid_types': (Int, Float),
                'additional_parameter': None,
                'linkname': 'y',
                'docstring': ('The right operand'),
            },
        })
        return methods

    def _get_input_valid_types(self, key):
        """Return the valid input types for the given key."""
        return self._use_methods[key]['valid_types']

    def _get_input_valid_type(self, key):
        """Return the valid input type for the given key."""
        valid_types = self._get_input_valid_types(key)

        if isinstance(valid_types, tuple):
            return valid_types[0]

        return valid_types

    def _prepare_for_submission(self, tempfolder, inputdict):
        """
        This method is called prior to job submission with a set of calculation input nodes.
        The inputs will be validated and sanitized, after which the necessary input files will
        be written to disk in a temporary folder. A CalcInfo instance will be returned that contains
        lists of files that need to be copied to the remote machine before job submission, as well
        as file lists that are to be retrieved after job completion.

        :param tempfolder: an aiida.common.folders.Folder to temporarily write files on disk
        :param inputdict: a dictionary with the raw input nodes
        :returns: CalcInfo instance
        """
        input_nodes = self.validate_input_nodes(inputdict)
        input_x = input_nodes[self.get_linkname('x')]
        input_y = input_nodes[self.get_linkname('y')]
        input_code = input_nodes[self.get_linkname('code')]

        self.write_input_files(tempfolder, input_x, input_y)

        retrieve_list = self.get_retrieve_list()
        local_copy_list = self.get_local_copy_list()
        remote_copy_list = self.get_remote_copy_list()

        codeinfo = CodeInfo()
        codeinfo.cmdline_params = ['-in', self._INPUT_FILE_NAME]
        codeinfo.stdout_name = self._OUTPUT_FILE_NAME
        codeinfo.code_uuid = input_code.uuid

        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.codes_info = [codeinfo]
        calcinfo.retrieve_list = retrieve_list
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list

        return calcinfo

    def get_retrieve_list(self):
        """
        Build the list of files that are to be retrieved upon calculation completion so that they can
        be passed to the parser.

        :returns: list of resource retrieval instructions
        """
        retrieve_list = []

        # Only the output file needs to be retrieved
        retrieve_list.append(self._OUTPUT_FILE_NAME)

        return retrieve_list

    @staticmethod
    def get_local_copy_list():
        """
        Build the local copy list, which are files that need to be copied from the local to the remote machine

        :returns: list of resource copy instructions
        """
        return []

    @staticmethod
    def get_remote_copy_list():
        """
        Build the remote copy list, which are files that need to be copied from the remote machine from one place
        to the directory of the new calculation on the same remote machine

        :returns: list of resource copy instructions
        """
        return []

    def validate_input_nodes(self, input_nodes_raw):
        """
        This function will validate that all required input nodes are present and that their content is valid

        :param input_nodes_raw: a dictionary with the raw input nodes
        :returns: dictionary with validated and sanitized input nodes
        """
        input_nodes = {}

        # Verify that all required inputs are provided in the raw input dictionary
        for input_key in self._required_inputs:
            try:
                input_link = self.get_linkname(input_key)
                input_node = input_nodes_raw.pop(input_key)
            except KeyError:
                raise InputValidationError("required input '{}' was not specified".format(input_key))

            input_nodes[input_link] = input_node

        # Check for optional inputs in the raw input dictionary, creating an instance of its valid types otherwise
        for input_key in self._optional_inputs:
            try:
                input_link = self.get_linkname(input_key)
                input_node = input_nodes_raw.pop(input_key)
            except KeyError:
                valid_type_class = self._get_input_valid_type(input_key)
                input_node = valid_type_class()

            input_nodes[input_link] = input_node

        # Any remaining input nodes are not recognized raise an input validation exception
        if input_nodes_raw:
            raise InputValidationError('the following input nodes were not recognized: {}'.format(
                input_nodes_raw.keys()))

        return input_nodes

    def write_input_files(self, tempfolder, input_x, input_y):
        """
        Take the input_parameters dictionary with the namelists and their flags
        and write the input file to disk in the temporary folder

        :param tempfolder: an aiida.common.folders.Folder to temporarily write files on disk
        :param input_x: the numeric node representing the left operand of the summation
        :param input_y: the numeric node representing the right operand of the summation
        """
        filename = tempfolder.get_abs_path(self._INPUT_FILE_NAME)

        with io.open(filename, 'w', encoding='utf8') as handle:
            handle.write(u'{} {}\n'.format(input_x.value, input_y.value))