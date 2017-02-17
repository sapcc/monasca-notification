from monasca_common.kafka import consumer, producer
from monasca_common.kafka_lib.common import KafkaError
from oslo_log import log as logging

from monasca_notification.monitoring.metrics import KAFKA_CONSUMER_ERRORS, KAFKA_PRODUCER_ERRORS
from monitoring import client

log = logging.getLogger(__name__)


class BaseEngine(object):
    def __init__(self, config, topic, path):
        self._topic_name = topic
        self._config = config
        self._statsd = client.get_client()
        self._consumer = consumer.KafkaConsumer(
            config['kafka']['url'],
            config['zookeeper']['url'],
            path,
            config['kafka']['group'],
            topic)
        self._consumer_errors = self._statsd.get_counter(name=KAFKA_CONSUMER_ERRORS,
                                                         dimensions={'topic': topic})
        self._producer = producer.KafkaProducer(config['kafka']['url'])

        self._producer_errors = self._statsd.get_counter(name=KAFKA_PRODUCER_ERRORS)

    def publish_messages(self, messages, topic):
        try:
            self._producer.publish(topic,
                                   [i.to_json() for i in messages])
        except KafkaError:
            log.exception("Notification encountered Kafka errors while publishing to topic %s", topic)
            self._producer_errors.increment(1, sample_rate=1.0, dimensions={'topic': topic})
            raise

    def do_message(self, message):
        """
        redefine this method to actually send messages
        :param message: message to be sent
        """
        raise NotImplemented

    def run(self):
        try:
            for message in self._consumer:
                self.do_message(message)

        except KafkaError:
            log.exception("Notification encountered Kafka errors while reading alarms")
            self._consumer_errors.increment(1)
            raise
