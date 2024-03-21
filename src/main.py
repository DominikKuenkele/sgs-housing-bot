import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import create_engine, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from database import Apartment, Base
from mail import Mail, SMTPServerConfig
from sgs import SGS, SGSFilter
from vasttrafik import VasttrafikAPI
from webdriver import get_webdriver

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class MissingEnvironmentVariable(Exception):
    pass


@dataclass
class ApartmentList:
    id: str
    address: str
    location: str
    size: str
    area: str
    rent: str
    free_from: str
    url: str
    time_to_school: str
    time_to_center: str
    time_to_bar: str


if __name__ == "__main__":
    engine = create_engine("sqlite:///database.db", echo=True)
    Base.metadata.create_all(engine)

    try:
        webdriver = get_webdriver(headless=True)

        log.info("opening SGS website...")
        crawled_apartments = SGS(webdriver).get_apartments(
            SGSFilter(min_area=25, max_rent=7200)
        )

        vasttrafik = VasttrafikAPI(
            "dFE2NzEzTk9KRU13dTVQc055bmVLSF9BN240YTp5bDMwQ1FPMUZMVGQxQnZEa0FQelFRTmV2N1Fh"
        )
        enriched_apartments = [
            ApartmentList(
                **apartment.__dict__,
                time_to_school=str(
                    vasttrafik.get_planned_duration(
                        "Eklandagatan 86", apartment.address
                    )
                ),
                time_to_center=str(
                    vasttrafik.get_planned_duration(
                        "Centralstationen", apartment.address
                    )
                ),
                time_to_bar=str(
                    vasttrafik.get_planned_duration("Järntorget", apartment.address)
                ),
            )
            for apartment in crawled_apartments
        ]

        log.info("storing apartments...")
        with Session(engine) as session:
            for apartment in enriched_apartments:
                statement = (
                    insert(Apartment)
                    .values(**apartment.__dict__)
                    .on_conflict_do_nothing()
                )
                session.execute(statement)

            session.commit()

        log.info("prepare notification")
        with Session(engine) as session:
            statement = select(Apartment).where(Apartment.notified == False)
            new_apartments = session.execute(statement).all()

            apartment_ids = [apartment[0].id for apartment in new_apartments]

            apartment_list = [
                f"""{apartment[0].address} - {apartment[0].location} (free from {datetime.strftime(apartment[0].free_from, "%-d %b")}):
{apartment[0].size} | {apartment[0].area}m² | {apartment[0].rent} SEK
To Eklandagatan: {apartment[0].time_to_school} | To Centralstation: {apartment[0].time_to_center} | To Järntorget: {apartment[0].time_to_bar}
{apartment[0].url}
"""
                for apartment in new_apartments
            ]

        log.info("found %s new apartments to send", len(apartment_list))
        if len(apartment_list) > 0:
            smtp_config = SMTPServerConfig(
                server="mail.dominik-kuenkele.de",
                port=465,
                user="hello@dominik-kuenkele.de",
                password="{g)Sc9B0K=x:V%QH1yyb=&3p",
            )
            mail = Mail(smtp_config)
            mail_content = "\n".join(apartment_list)

            mail.send(
                subject="New SGS apartments",
                sender="admin@dominik-kuenkele.de",
                receivers=["hello@dominik-kuenkele.de", "salve.salvestri@gmail.com"],
                content=mail_content,
            )

            log.info("Update database...")
            with Session(engine) as session:
                statement = (
                    update(Apartment)
                    .where(Apartment.id.in_(apartment_ids))
                    .values(notified=True)
                )

                session.execute(statement)
                session.commit()
        else:
            log.info("No mail sent.")

    except:
        log.error("Failed.", exc_info=True)
    finally:
        webdriver.quit()
