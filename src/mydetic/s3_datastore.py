"""
DataStore implementation that stores data in an S3 Bucket.
"""

import boto
from boto.s3.key import Key
from boto.s3.connection import Location
from datastore import DataStore
from exceptions import MyDeticMemoryAlreadyExists, MyDeticMemoryException, MyDeticNoMemoryFound
from memorydata import MemoryData


class S3DataStore(DataStore):
    """
    S3 implementation of DataStore.
    This class doesn't catch boto.exception - you should handle it upstream.
    """

    def __init__(self, s3_config=None):
        """
        Constructor
        :param s3_config: Dictionary containing S3 connection details.
        """
        DataStore.__init__(self)
        if s3_config is not None:
            self.validate_s3_params(s3_config)
        self._s3_config = s3_config

        if len(self._s3_config['region']) > 0:
            self._connection = boto.s3.connect_to_region(self._s3_config['region'])
        else:
            self._connection = boto.connect_s3()

        self._bucket = None

    def create_bucket_if_required(self):
        if self._bucket is None:
            self._bucket = self._connection.create_bucket(self._s3_config['bucket'], location=self._s3_config['region'])
        return self._bucket

    @staticmethod
    def validate_s3_params(s3_config):
        """
        Check that everything is tickety-boo with the s3 params. Just
        check that they're all there, not that they're right.
        :param s3_config: Dictionary containing S3 connection details.
        :raises: ValueError
        """
        missing_params = []
        for required_param in ['region', 'aws_access_key_id', 'aws_secret_access_key', 'bucket', 'region']:
            if required_param not in s3_config:
                missing_params.append(required_param)
        if len(missing_params) > 0:
            raise ValueError("s3 config is missing [%s]" % ','.join(missing_params))

    @staticmethod
    def generate_memory_key_name(user_id, memory_date):
        """

        :param user_id: user id string
        :param memory_date: a datetime.date
        :return: a key name for the memory ("user_id/YYYYMMDD.json")
        """
        user_id_str = user_id
        if type(user_id) is unicode:
            user_id_str = user_id.encode('utf-8')
        return "%s/%s.json" % (user_id_str, memory_date.strftime("%Y%m%d"))

    def get_memory(self, user_id, memory_date):
        """
        :param user_id: str the User ID
        :type user_id: str or unicode
        :param memory_date:
        :type memory_date: datetime.date
        :return: The memory
        :raises MyDeticNoMemoryFound if there isn't a memory on this day
        """
        self.create_bucket_if_required()
        k = self._bucket.get_key(self.generate_memory_key_name(user_id, memory_date))
        if k is None:
            raise MyDeticNoMemoryFound(user_id, memory_date)
        return MemoryData.from_json_str(k.get_contents_as_string())

    def has_memory(self, user_id, memory_date):
        """
        Return whether a memory exists for a user at a date.
        :param user_id:
        :type user_id: str or unicode
        :param memory_date:
        :type memory_date: datetime.date
        :return: True if a memory exists, false otherwise.
        """
        self.create_bucket_if_required()
        k = self._bucket.get_key(self.generate_memory_key_name(user_id, memory_date))
        return k is not None

    def update_memory(self, user_id, memory_date, memory):
        self.create_bucket_if_required()
        return DataStore.update_memory(self, user_id, memory_date, memory)

    def add_memory(self, user_id, memory_date, memory):
        """

        :param user_id:
        :type user_id: str or unicode
        :param memory_date:
        :param memory:
        :raises MyDeticMemoryAlreadyExists
        :return:
        """
        self.create_bucket_if_required()
        if self.has_memory(user_id, memory_date):
            raise MyDeticMemoryAlreadyExists(user_id, memory_date)

        bucket = self._bucket
        k = Key(bucket)
        k.key = self.generate_memory_key_name(user_id, memory_date)
        k.set_contents_from_string(memory.as_json_str())

    def list_memories(self, user_id, start_date=None, end_date=None):
        return DataStore.list_memories(self, user_id, start_date, end_date)

    def delete_memory(self, user_id, memory_date, memory):
        return DataStore.delete_memory(self, user_id, memory_date, memory)