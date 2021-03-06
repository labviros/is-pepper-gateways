from is_wire.core import Channel, Message, Logger, Status, StatusCode
from is_wire.rpc import ServiceProvider, LogInterceptor

from google.protobuf.empty_pb2 import Empty
from google.protobuf.struct_pb2 import Struct
from is_msgs.common_pb2 import FieldSelector, Position, Pose
from is_msgs.robot_pb2 import RobotConfig
from is_msgs.camera_pb2 import FrameTransformations

import socket


def get_obj(callable, obj):
    value = callable()
    if value is not None:
        obj.CopyFrom(value)


def get_val(callable, obj, attr):
    value = callable()
    if value is not None:
        setattr(obj, attr, value)


class RobotGateway(object):
    def __init__(self, driver):
        self.driver = driver
        self.logger = Logger("RobotGateway")

    def get_config(self, field_selector, ctx):
        robot_config = RobotConfig()
        get_obj(self.driver.get_speed, robot_config.speed)
        return robot_config

    def set_config(self, robot_config, ctx):
        if robot_config.HasField("speed"):
            self.driver.set_speed(robot_config.speed)
        return Empty()

    def navigate_to(self, position, ctx):
        self.driver.navigate_to(position.x, position.y)
        return Empty()

    def move_to(self, pose, ctx):
        self.driver.move_to(pose.position.x, pose.position.y,pose.orientation.yaw)
        return Empty()

    def pause_awareness(self, req, ctx):
        self.driver.pause_awareness()
        return Empty()

    def resume_awareness(self, req, ctx):
        self.driver.resume_awareness()
        return Empty()

    def set_awareness(self, req, ctx):
        self.driver.set_awareness(req["enabled"])
        return Empty()

    #def set_awareness_off(self, req, ctx):
    #    self.driver.set_awareness_off()
    #    return Empty()



    def run(self, id, broker_uri):
        service_name = "RobotGateway.{}".format(id)

        channel = Channel(broker_uri)
        server = ServiceProvider(channel)
        logging = LogInterceptor()
        server.add_interceptor(logging)

        server.delegate(
            topic=service_name + ".GetConfig",
            request_type=FieldSelector,
            reply_type=RobotConfig,
            function=self.get_config)

        server.delegate(
            topic=service_name + ".SetConfig",
            request_type=RobotConfig,
            reply_type=Empty,
            function=self.set_config)

        server.delegate(
            topic=service_name + ".NavigateTo",
            request_type=Position,
            reply_type=Empty,
            function=self.navigate_to)

        server.delegate(
            topic=service_name + ".MoveTo",
            request_type=Pose,
            reply_type=Empty,
            function=self.move_to)

        server.delegate(
            topic=service_name + ".PauseAwareness",
            request_type=Empty,
            reply_type=Empty,
            function=self.pause_awareness)

        server.delegate(
            topic=service_name + ".ResumeAwareness",
            request_type=Empty,
            reply_type=Empty,
            function=self.resume_awareness)

        server.delegate(
            topic=service_name + ".SetAwareness",
            request_type=Struct,
            reply_type=Empty,
            function=self.set_awareness)


        #server.delegate(
        #    topic=service_name + ".SetAwarenessOff",
        #    request_type=Empty,
        #    reply_type=Empty,
        #    function=self.set_awareness_off)


        self.logger.info("Listening for requests")
        while True:
            pose = self.driver.get_base_pose()
            frameTransList = FrameTransformations()
            frameTransList.tfs.extend([pose])
            self.logger.debug("Publishing pose")

            channel.publish(
                Message(content=frameTransList), topic=service_name + ".FrameTransformations")

            try:
                message = channel.consume(timeout=0)
                if server.should_serve(message):
                    server.serve(message)
            except socket.timeout:
                pass
