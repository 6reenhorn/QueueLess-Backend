from rest_framework.throttling import AnonRateThrottle


class JoinQueueRateThrottle(AnonRateThrottle):
    scope = "join"


class BurstRateThrottle(AnonRateThrottle):
    scope = "burst"
