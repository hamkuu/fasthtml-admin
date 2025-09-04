from fasthtml.common import *
from fasthtml.oauth import GoogleAppClient, OAuth
from fastlite import database

from dataclasses import dataclass
from starlette.responses import RedirectResponse
from monsterui.all import *

import os


def user_auth_before(req, sess):
    auth = req.scope["auth"] = sess.get("auth", None)
    return None if auth else RedirectResponse("/", status_code=303)


before = Beforeware(
    user_auth_before, skip=[r"/favicon\.ico", r"/static/.*", r".*\.css", r".*\.js", "/login", "/", "/redirect"]
)

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
        A("Admin", href="/admin"),
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
                Img(src=user.picture, alt="User Picture"),
                P(f"Available Credits: {user.credits}"),
            ),
            cls="py-10",
        ),
    )


@rt
def theme():
    return (
        ex_navbar1(),
        ThemePicker(color=True, radii=True, shadows=True, font=True, mode=True),
    )


@rt("/admin")
def admin(sess):
    # Restrict access to certain users
    current = db.users("oauth_id=?", (sess["auth"],))[0]
    if not (current.email.startswith("hamkuu") or current.email.endswith("@nablas.com")):
        return Titled("Forbidden", P("You do not have access to this page."))

    header = ["ID", "Email", "Name", "Credits", "Actions"]
    rows = []
    for u in db.users():
        rows.append([u.id, u.email, u.name, u.credits, edit_modal(uid=u.id)])

    table = TableFromLists(header, rows, cls=(TableT.striped, TableT.hover))

    return (
        ex_navbar1(),
        Container(H2("Users Admin"), table, Div(id="modal")),
    )


def edit_modal(uid: int):
    user = db.users[uid]
    return (
        Button("Edit", cls=ButtonT.primary, data_uk_toggle="target: #edit-modal"),
        Modal(
            ModalTitle("Edit Credits"),
            Form(action=update_credit, method="post")(
                Input(type="hidden", name="uid", value=user.id),
                Input(type="number", name="new_credits", value=user.credits),
                Button("Save", cls=ButtonT.primary, type="submit"),
            ),
            footer=ModalCloseButton("Close", cls=ButtonT.secondary),
            id="edit-modal",
        ),
    )


@rt
def update_credit(uid: int, new_credits: int):
    user = db.users[uid]
    user.credits = new_credits
    db.users.update(user)
    return RedirectResponse("/admin", status_code=303)


serve()
