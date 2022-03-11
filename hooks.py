from sqlalchemy.event import listen
from CTFd.models import Users, Solves, Challenges
from .db_utils import DBUtils
from ...utils.modes import get_model
import CTFd.cache as cache

import json
import requests as rq


def discord_notify(solve, webhookurl):
    text = _getText(solve)

    embed = {
        "title": "First Blood!",
        "color": 15158332,
        "description": text
    }

    data = {"embeds": [embed]}

    try:
        rq.post(webhookurl, data=json.dumps(data), headers={"Content-Type": "application/json"})
    except rq.exceptions.RequestException as e:
        print(e)


def cliq_notify(solve, cliq_url, cliq_token):
    text = _getText(solve)
    uri = cliq_url + "?zapikey=" + cliq_token
    embed = {
        "text": text["body"],
        "solvedBy": text["user"],
        "challenge": text["challenge"],
        "points": text["points"]
    }

    try:
        rq.post(uri, data=json.dumps(embed), headers={"Content-Type": "application/json"})
    except rq.exceptions.RequestException as e:
        print(e)



def on_solve(mapper, conn, solve):
    config = DBUtils.get_config()
    solves = _getSolves(solve.challenge_id)

    if solves == 1:
        if config.get("discord_notifier") == "true":
            discord_notify(solve, config.get("discord_webhook_url"))

        if config.get("cliq_notifier") == "true":
            cliq_notify(solve, config.get("cliq_url"), config.get("cliq_token"))


def _getSolves(challenge_id):
    Model = get_model()

    solve_count = (
        Solves.query.join(Model, Solves.account_id == Model.id)
            .filter(
            Solves.challenge_id == challenge_id,
            Model.hidden == False,
            Model.banned == False,
        )
            .count()
    )

    return solve_count


def _getChallenge(challenge_id):
    challenge = Challenges.query.filter_by(id=challenge_id).first()
    return challenge


def _getUser(user_id):
    user = Users.query.filter_by(id=user_id).first()
    return user


def _getText(solve, hashtags=""):
    cache.clear_standings()
    user = _getUser(solve.user_id)
    challenge = _getChallenge(solve.challenge_id)
    points = challenge.value

    score = user.get_score(admin=True)
    place = user.get_place(admin=True)

    if not hashtags == "":
        text = f"{user.name} got first blood on {challenge.name} and is now in {place} place with {score} points! {hashtags}"
    else:
        text = f"Challenge ❝{challenge.name}❞ was solved by {user.name} and is now in {place} place with {score} point(s)!"

    return {
        "body": text,
        "points": points,
        "user": user.name,
        "challenge": challenge.name
    }


def load_hooks():
    listen(Solves, "after_insert", on_solve)
