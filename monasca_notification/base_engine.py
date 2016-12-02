from kafka import common
from monasca_common.kafka import consumer, producer
from monitoring import client
from oslo_log import log as logging

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
        self._producer = producer.KafkaProducer(config['kafka']['url'])

    def publish_messages(self, messages, topic, error_counter):
        try:
            self._producer.publish(topic,
                                   [i.to_json() for i in messages])
            error_counter.increment(0, sample_rate=0.01)
        except common.KafkaError:
            log.exception("Notification encountered Kafka errors while reading from topic %s", topic)
            error_counter.increment(1)
            raise
