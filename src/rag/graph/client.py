"""Neo4j async client managing connections to Neo4j Aura."""

import logging

from neo4j import AsyncDriver, AsyncGraphDatabase

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
        database: str = "neo4j",
    ):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self._driver: AsyncDriver | None = None

    def get_driver(self) -> AsyncDriver:
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_lifetime=3600,
                keep_alive=True,
                connection_timeout=30.0,
            )
        return self._driver

    async def verify_connectivity(self) -> None:
        driver = self.get_driver()
        await driver.verify_connectivity()
        logger.info("Neo4j connectivity verified: %s", self.uri)

    def session(self):
        return self.get_driver().session(database=self.database)

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j driver connection closed.")
