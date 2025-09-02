from fasthtml.common import *
from fasthtml.oauth import GoogleAppClient, OAuth
from fastlite import database

from dataclasses import dataclass
from starlette.responses import RedirectResponse
from monsterui.all import *

import os

PRODUCTION = os.getenv("PRODUCTION", "").lower() in ("1", "true")

if PRODUCTION:
    app, rt = fast_app(hdrs=Theme.blue.headers())
    db = database(":memory:")
else:
    app, rt = fast_app(hdrs=Theme.blue.headers(), live=True, debug=True)
    db = database("database/users.db")


@dataclass
class User:
    id: Optional[int] = None
    email: str = ""
    name: str = ""
    picture: str = ""
    oauth_id: str = ""
    credits: int = 0


db.users = db.create(User, transform=True)


class Auth(OAuth):
    def get_auth(self, info, ident, sess, state):
        sess["auth"] = info.sub
        user = db.users("oauth_id=?", (sess["auth"],))
        if not user:
            db.users.insert(User(oauth_id=sess["auth"], email=info.email, name=info.name, picture=info.picture))
        return RedirectResponse("/home", status_code=303)


client = GoogleAppClient(os.getenv("GOOGLE_CLIENT_ID"), os.getenv("GOOGLE_CLIENT_SECRET"))
oauth = Auth(app, client, skip=("/", "/logout", "/redirect"), login_path="/")


def ex_navbar1():
    return NavBar(
        A("Home", href="/home"),
        A("Users", href="/admin/users"),
        A("Theme", href="/theme"),
        A("Logout", href="/logout"),
        brand=H3("FastHTML"),
        sticky=True,
    )


@rt
def index(req):
    return Center(
        DivVStacked(
            H1("Welcome"),
            A(UkIcon("log-in"), "Login with Google", href=oauth.login_link(req), cls=(ButtonT.primary, "btn")),
            Small(
                A(cls=AT.muted, href="#demo")("Terms of Service"),
                cls=(TextT.muted, "text-center"),
            ),
        ),
        cls="h-screen",
    )


@rt
def home(sess):
    user = db.users("oauth_id=?", (sess["auth"],))[0]
    return (
        ex_navbar1(),
        Center(
            DivVStacked(
                H2(f"Welcome, {user.name}!"),
                Subtitle(f"Email: {user.email}"),
                Img(src=user.picture, alt="User Picture", cls="w-24 h-24 rounded-full", referrerpolicy="no-referrer"),
            ),
            cls="py-10",
        ),
    )


@rt
def theme():
    return Container(
        DivVStacked(
            A(UkIcon("arrow-left"), "Back", href="javascript:history.back()", cls=(ButtonT.secondary, "btn")),
            ThemePicker(color=True, radii=True, shadows=True, font=True, mode=True, cls="p-4", custom_themes=[]),
        )
    )


@rt("/admin/users")
def admin_users(sess):
    if not sess.get("auth"):
        return RedirectResponse("/", status_code=303)

    # Restrict access to certain users
    current = db.users("oauth_id=?", (sess["auth"],))[0]
    if not (current.email.startswith("hamkuu") or current.email.endswith("@nablas.com")):
        return Titled("Forbidden", P("You do not have access to this page."))

    header = ["ID", "Email", "Name", "Credits", "Actions"]

    rows = []
    for u in db.users():
        rows.append(
            [
                u.id,
                u.email,
                u.name,
                u.credits,
                Button(
                    "Edit",
                    type="button",
                    hx_get=edit_credit.to(id=u.id),
                    hx_target="#modal",
                    hx_swap="innerHTML",
                    cls=ButtonT.secondary,
                ),
            ]
        )

    table = TableFromLists(header, rows, cls=(TableT.striped, TableT.hover))

    return (
        ex_navbar1(),
        Container(
            H2("User Administration"),
            table,
            Div(id="modal"),
        ),
    )


@rt
def edit_credit(id: int):
    user = db.users[id]
    if not user:
        return P("User not found")

    form = Form(action=update_credit, method="post")(
        Input(type="hidden", name="id", value=user.id),
        Input(type="number", name="credits", value=user.credits, cls="w-20 text-center"),
        Button("Save", cls=ButtonT.primary, type="submit", size="sm"),
        A("Cancel", href="/admin/users", cls=ButtonT.secondary),  # link back to list
    )
    return Titled("Edit Credits", form)


@rt
def update_credit(id: int, credits: int):
    user = db.users[id]
    if not user:
        return P("User not found")
    user.credits = credits
    db.users.update(user)
    return RedirectResponse("/admin/users", status_code=303)


serve()
