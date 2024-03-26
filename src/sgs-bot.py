import argparse
import logging
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, create_engine, delete, event, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from database import (
    Apartment,
    Base,
    Destination,
    Distance,
    SubscribedApartments,
    Subscription,
)
from mail import MailSendException, MailServer, SMTPServerConfig
from sgs import SGS
from vasttrafik import VasttrafikAPI
from webdriver import get_webdriver

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@dataclass
class Config:
    data_root: str
    vasttrafik_api_key: str
    smpt_server: str
    smtp_port: str
    smtp_user: str
    smtp_password: str


class MissingEnvironmentVariable(Exception):
    pass


def load_config():
    try:
        with open(os.environ["SMTP_SERVER_FILE"], encoding="utf-8") as f:
            smtp_server = f.read().strip()
        with open(os.environ["SMTP_PORT_FILE"], encoding="utf-8") as f:
            smtp_port = f.read().strip()
        with open(os.environ["SMTP_USER_FILE"], encoding="utf-8") as f:
            smtp_user = f.read().strip()
        with open(os.environ["SMTP_PASSWORD_FILE"], encoding="utf-8") as f:
            smtp_password = f.read().strip()
        with open(os.environ["VASTTRAFIK_API_KEY_FILE"], encoding="utf-8") as f:
            vasttrafik_api_key = f.read().strip()

        return Config(
            data_root="/var/lib/sgs-housing-bot/",
            smpt_server=smtp_server,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            vasttrafik_api_key=vasttrafik_api_key,
        )

    except KeyError as e:
        log.error("Failed reading the environment variable %s", e.args[0])
        raise MissingEnvironmentVariable(
            f"The environment variable '{e.args[0]}' is missing. Ensure to export it."
        ) from None


def store_appartments(session, apartments):
    for apartment in apartments:
        statement = (
            insert(Apartment).values(**apartment.__dict__).on_conflict_do_nothing()
        )
        session.execute(statement)

    session.commit()


def get_filtered_apartments(session: Session):
    statement = (
        select(Apartment, Subscription, Destination)
        .join(Destination, isouter=True)
        .where(Apartment.area > Subscription.min_area)
        .where(Apartment.rent < Subscription.max_rent)
    )
    result = session.execute(statement)
    return result.all()


def store_duration(session, apartment, destination, duration):
    statement = (
        insert(Distance)
        .values(
            {
                "apartment_id": apartment.id,
                "destination_id": destination.id,
                "time": duration,
            }
        )
        .on_conflict_do_update(
            set_={Distance.time: duration},
        )
    )
    session.execute(statement)
    session.commit()


def store_subscribed_apartment(session, apartment, subscription):
    statement = (
        insert(SubscribedApartments)
        .values(
            {
                "apartment_id": apartment.id,
                "subscription_id": subscription.id,
                "notified": False,
            }
        )
        .on_conflict_do_nothing()
    )

    session.execute(statement)
    session.commit()


def get_new_apartments(session):
    statement = (
        select(Subscription, Apartment, Distance, Destination)
        .join(
            SubscribedApartments,
            SubscribedApartments.subscription_id == Subscription.id,
        )
        .join(
            Apartment,
            SubscribedApartments.apartment_id == Apartment.id,
        )
        .join(Distance, isouter=True)
        .join(
            Destination,
            and_(
                Destination.id == Distance.destination_id,
                Destination.subscription_id == Subscription.id,
            ),
            isouter=True,
        )
        .where(SubscribedApartments.notified == False)
    )
    return session.execute(statement).all()


def get_notification(apartments):
    notifications = defaultdict(dict)
    for subscription, apartment, distance, destination in apartments:
        if apartment in notifications[subscription]:
            notifications[subscription][apartment][destination] = distance
        else:
            notifications[subscription][apartment] = {destination: distance}
    return notifications


def format_mail(apartment_dict):
    return [
        f"""{apartment.address} - {apartment.location} (free from {datetime.strftime(apartment.free_from, "%-d %b")}):
{apartment.size} | {apartment.area}m² | {apartment.rent} SEK
{" | ".join([f"To {destination.destination}: {distance.time}min" for destination, distance in distances.items()]) if list(distances.keys())[0] is not None else ""}
{apartment.url}
"""
        for apartment, distances in apartment_dict.items()
    ]


def store_sent_apartments(session, apartment_dict, subscription, value):
    statement = (
        update(SubscribedApartments)
        .where(
            SubscribedApartments.apartment_id.in_(
                [apartment.id for apartment in apartment_dict.keys()]
            )
        )
        .where(SubscribedApartments.subscription_id == subscription.id)
        .values(notified=value)
    )

    session.execute(statement)
    session.commit()


def get_db_engine(data_root):
    engine = create_engine(f"sqlite:///{os.path.join(data_root, 'database.db')}")
    Base.metadata.create_all(engine)

    return engine


def crawl(config, engine, _args):
    try:
        webdriver = get_webdriver(headless=True)

        log.info("opening SGS website...")
        crawled_apartments = SGS(webdriver).get_apartments()
    except Exception:
        log.error("Failed.", exc_info=True)
        sys.exit(1)
    finally:
        webdriver.quit()

    with Session(engine) as session:
        log.info("storing all apartments...")
        store_appartments(session, crawled_apartments)
        rows = get_filtered_apartments(session)

        log.info("calculate distances for %s combinations", len(rows))
        vasttrafik = VasttrafikAPI(config.vasttrafik_api_key, config.data_root)
        for apartment, subscription, destination in rows:
            if destination is not None:
                duration = (
                    vasttrafik.get_planned_duration(
                        apartment.address, destination.destination
                    ).total_seconds()
                    / 60
                )
                store_duration(session, apartment, destination, duration)

            store_subscribed_apartment(session, apartment, subscription)

        log.info("prepare notification")

        new_apartments = get_new_apartments(session)

    notifications = get_notification(new_apartments)

    mail_server = MailServer(
        SMTPServerConfig(
            config.smpt_server,
            config.smtp_port,
            config.smtp_user,
            config.smtp_password,
        )
    )
    for subscription, apartment_dict in notifications.items():
        apartment_list = format_mail(apartment_dict)

        log.info(
            "found %(number)s new apartments to send to %(email)s",
            {"number": len(apartment_list), "email": subscription.email},
        )
        if len(apartment_list) > 0:
            mail_content = "\n".join(apartment_list)
            mail_server.register_message(
                subject="New SGS apartments",
                receiver=subscription.email,
                content=mail_content,
            )
            log.info("Update database...")
            with Session(engine) as session:
                store_sent_apartments(session, apartment_dict, subscription, True)

    try:
        mail_server.send_all(attempts=3)
    except MailSendException:
        with Session(engine) as session:
            store_sent_apartments(session, apartment_dict, subscription, False)


def add_subscription(_config, engine, args):
    with Session(engine) as session:
        statement = (
            insert(Subscription)
            .values(
                {
                    "email": args.email,
                    "max_rent": args.max_rent,
                    "min_area": args.min_area,
                }
            )
            .returning(Subscription.id)
        )
        result = session.execute(statement)
        subscription_id = result.first()[0]

        if args.destinations is not None:
            destinations = [
                {"subscription_id": subscription_id, "destination": destination}
                for destination in args.destinations
            ]

            statement = insert(Destination).values(destinations)
            session.execute(statement)

        session.commit()


def remove_subscription(_config, engine, args):
    with Session(engine) as session:
        statement = delete(Subscription).where(Subscription.email == args.email)
        session.execute(statement)
        session.commit()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)
    subscription_parser = subparsers.add_parser("subscription")
    subscription_sub_parser = subscription_parser.add_subparsers(required=True)
    add_subscription_parser = subscription_sub_parser.add_parser("add")
    add_subscription_parser.add_argument("--email", type=str, required=True)
    add_subscription_parser.add_argument("--max_rent", type=int, default=100000)
    add_subscription_parser.add_argument("--min_area", type=int, default=0)
    add_subscription_parser.add_argument("--destinations", nargs="*")
    add_subscription_parser.set_defaults(func=add_subscription)

    add_subscription_parser = subscription_sub_parser.add_parser("remove")
    add_subscription_parser.add_argument("--email", type=str, required=True)
    add_subscription_parser.set_defaults(func=remove_subscription)

    crawl_apartments = subparsers.add_parser("crawl")
    crawl_apartments.set_defaults(func=crawl)

    args = parser.parse_args()

    config = load_config()
    os.makedirs(config.data_root, exist_ok=True)
    engine = get_db_engine(config.data_root)

    args.func(config, engine, args)
