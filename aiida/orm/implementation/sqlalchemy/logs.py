# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida_core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
"""SQLA Log and LogCollection module"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from aiida.backends.sqlalchemy import get_scoped_session
from aiida.backends.sqlalchemy.models.log import DbLog
from .. import BackendLog, BackendLogCollection
from . import entities
from . import utils


class SqlaLog(entities.SqlaModelEntity[DbLog], BackendLog):
    """SQLA Log backend entity"""

    MODEL_CLASS = DbLog

    def __init__(self, backend, time, loggername, levelname, objname, objpk=None, message="", metadata=None):
        # pylint: disable=too-many-arguments
        super(SqlaLog, self).__init__(backend)
        self._dbmodel = utils.ModelWrapper(
            DbLog(
                time=time,
                loggername=loggername,
                levelname=levelname,
                objname=objname,
                objpk=objpk,
                message=message,
                metadata=metadata))

    @property
    def time(self):
        """
        Get the time corresponding to the entry
        """
        return self._dbmodel.time

    @property
    def loggername(self):
        """
        The name of the logger that created this entry
        """
        return self._dbmodel.loggername

    @property
    def levelname(self):
        """
        The name of the log level
        """
        return self._dbmodel.levelname

    @property
    def objpk(self):
        """
        Get the id of the object that created the log entry
        """
        return self._dbmodel.objpk

    @property
    def objname(self):
        """
        Get the name of the object that created the log entry
        """
        return self._dbmodel.objname

    @property
    def message(self):
        """
        Get the message corresponding to the entry
        """
        return self._dbmodel.message

    @property
    def metadata(self):
        """
        Get the metadata corresponding to the entry
        """
        return self._dbmodel._metadata  # pylint: disable=protected-access


class SqlaLogCollection(BackendLogCollection):
    """The SQLA collection for logs"""

    ENTITY_CLASS = SqlaLog

    def delete_many(self, filters):
        """
        Delete all log entries in the table
        """
        if not filters:
            for entry in DbLog.query.all():
                entry.delete()
            get_scoped_session().commit()
        else:
            raise NotImplementedError("Only deleting all by passing an empty filer dictionary is "
                                      "currently supported")