"""Builds planning-examples.jsonl: hand-written example plans in the Planning stage's
labelled-line format, used for few-shot retrieval (orchestrator/retrieval.py).

Every plan is run through orchestrator/planning_format.parse_plan, so an example that the
real parser would reject cannot be written. Run: python build_planning_examples.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
from plan_eval import score  # noqa: E402
from planning_format import parse_plan  # noqa: E402

EXAMPLES = [
    (
        "A to-do list app with sign up, adding and completing tasks, and a progress summary",
        """TYPE: web_app
MODULE: Account | Sign up and get into your account
FEATURE: Sign up | WHEN a new user submits an email and password | THEN an account is created and they are signed in
FEATURE: Sign in | WHEN a returning user enters their email and password | THEN they are signed in to their tasks
SCREEN: signup | Sign up | Create an account
MODULE: Task management | Add, view and complete your to-dos
FEATURE: Add a task | WHEN the user types a title and presses Add | THEN the task appears in the list
FEATURE: Complete a task | WHEN the user ticks a task | THEN it is shown as done
SCREEN: list | Task List | Shows all tasks
SCREEN: add | Add Task | Form to create a task
MODULE: Progress | See how much you have done
FEATURE: Progress summary | WHEN the user opens the summary | THEN it shows completed vs total tasks
FEATURE: Completion rate | WHEN the user opens the summary | THEN the percentage of tasks done is shown
SCREEN: summary | Progress | Completed and total task counts
FLOW: signup -> list | submit sign up form
FLOW: list -> add | click Add task
FLOW: add -> list | click Save
FLOW: list -> summary | click Progress""",
    ),
    (
        "A personal portfolio website for a photographer with galleries and a contact form",
        """TYPE: portfolio
MODULE: Galleries | Show off your best photos
FEATURE: Browse galleries | WHEN a visitor opens the home page | THEN they see a grid of gallery covers
FEATURE: View a gallery | WHEN a visitor clicks a gallery | THEN its photos are shown full size
SCREEN: home | Home | Grid of gallery covers
SCREEN: gallery | Gallery | Photos in one gallery
MODULE: About and contact | Let people get in touch
FEATURE: About page | WHEN a visitor opens About | THEN they read the photographer's story
FEATURE: Contact form | WHEN a visitor submits the contact form | THEN the message is sent and a thank-you is shown
SCREEN: about | About | The photographer's story
SCREEN: contact | Contact | Message form
FLOW: home -> gallery | click a gallery
FLOW: gallery -> home | click Back
FLOW: home -> about | click About
FLOW: home -> contact | click Contact""",
    ),
    (
        "A blog where an author writes posts and readers can read and comment",
        """TYPE: blog
MODULE: Reading | Read posts and join the conversation
FEATURE: List posts | WHEN a reader opens the blog | THEN the newest posts are listed
FEATURE: Read a post | WHEN a reader clicks a post | THEN the full post is shown
FEATURE: Comment on a post | WHEN a reader submits a comment | THEN it appears under the post
SCREEN: posts | Posts | Newest posts first
SCREEN: post | Post | One post with its comments
MODULE: Writing | Publish your posts
FEATURE: Write a post | WHEN the author saves a new post | THEN it is published to the blog
FEATURE: Edit a post | WHEN the author changes a post and saves | THEN readers see the new version
SCREEN: editor | Editor | Write or edit a post
FLOW: posts -> post | click a post
FLOW: post -> posts | click Back
FLOW: posts -> editor | click New post
FLOW: editor -> posts | click Publish""",
    ),
    (
        "An online shop for handmade candles with a cart and checkout",
        """TYPE: ecommerce
MODULE: Catalog | Find a candle you like
FEATURE: Browse products | WHEN a shopper opens the shop | THEN candles are listed with price and photo
FEATURE: Product details | WHEN a shopper clicks a candle | THEN its description and price are shown
SCREEN: shop | Shop | List of candles
SCREEN: product | Product | One candle in detail
MODULE: Cart and checkout | Buy what you picked
FEATURE: Add to cart | WHEN a shopper clicks Add to cart | THEN the candle is added and the cart count goes up
FEATURE: Checkout | WHEN a shopper submits name and address | THEN the order is placed and confirmed
SCREEN: cart | Cart | Items and total
SCREEN: checkout | Checkout | Delivery details form
FLOW: shop -> product | click a candle
FLOW: product -> cart | click Add to cart
FLOW: cart -> checkout | click Checkout
FLOW: checkout -> shop | place order""",
    ),
    (
        "An internal tool for a small warehouse to track stock levels and low-stock alerts",
        """TYPE: internal_tool
MODULE: Inventory | Track the stock levels in your warehouse
FEATURE: List stock | WHEN staff open the tool | THEN all items and quantities are shown
FEATURE: Update quantity | WHEN staff change a quantity and save | THEN the new stock level is stored
FEATURE: Add an item | WHEN staff submit a new item form | THEN the item appears in the list
SCREEN: stock | Stock List | Items and quantities
SCREEN: item | Edit Item | Change or add an item
MODULE: Alerts | Never run out unnoticed
FEATURE: Low-stock alert | WHEN an item falls below its minimum | THEN it is highlighted on the alerts screen
FEATURE: Set a minimum level | WHEN staff set a minimum quantity for an item | THEN alerts use that level
SCREEN: alerts | Low Stock | Items below their minimum
FLOW: stock -> item | click an item
FLOW: item -> stock | click Save
FLOW: stock -> alerts | click Alerts""",
    ),
    (
        "A mobile fitness tracker to log workouts and see weekly totals",
        """TYPE: mobile_app
MODULE: Workouts | Track your fitness by logging what you did
FEATURE: Log a workout | WHEN the user enters type and minutes and saves | THEN the workout is added to today
FEATURE: Workout history | WHEN the user opens history | THEN past workouts are listed by day
SCREEN: log | Log Workout | Enter a workout
SCREEN: history | History | Past workouts
MODULE: Progress | See how the week went
FEATURE: Weekly totals | WHEN the user opens the weekly view | THEN total minutes per day are shown
FEATURE: Streak | WHEN the user logs a workout on consecutive days | THEN the current streak is shown
SCREEN: week | This Week | Minutes per day
FLOW: log -> history | tap History
FLOW: history -> log | tap Add
FLOW: history -> week | tap This week""",
    ),
    (
        "A web app for a hair salon where customers book appointments",
        """TYPE: web_app
MODULE: Booking | Pick a time that suits you
FEATURE: See open slots | WHEN a customer chooses a day | THEN free time slots are listed
FEATURE: Book a slot | WHEN a customer picks a slot and enters their name | THEN the appointment is confirmed
FEATURE: Cancel a booking | WHEN a customer cancels an appointment | THEN the slot becomes free again
SCREEN: slots | Choose a Time | Days and free slots
SCREEN: confirm | Confirm Booking | Name and confirmation
MODULE: Salon admin | Keep the diary tidy
FEATURE: Daily schedule | WHEN the owner opens today | THEN all booked appointments are listed in time order
FEATURE: Block time off | WHEN the owner blocks a time range | THEN those slots can no longer be booked
SCREEN: schedule | Today | The owner's schedule
FLOW: slots -> confirm | click a slot
FLOW: confirm -> slots | click Done
FLOW: slots -> schedule | owner opens Today""",
    ),
    (
        "An expense tracker where I add spending by category and see monthly totals",
        """TYPE: web_app
MODULE: Spending | Record what you spend
FEATURE: Add an expense | WHEN the user enters amount, category and date and saves | THEN the expense is stored
FEATURE: List expenses | WHEN the user opens the list | THEN expenses are shown newest first
FEATURE: Delete an expense | WHEN the user deletes an expense | THEN it is removed from the list
SCREEN: expenses | Expenses | All expenses
SCREEN: add | Add Expense | Form to add spending
MODULE: Reports | Understand your month
FEATURE: Monthly totals | WHEN the user opens the report | THEN totals per category for the month are shown
FEATURE: Spending trend | WHEN the user compares months | THEN the change from last month is shown
SCREEN: report | Monthly Report | Totals by category
FLOW: expenses -> add | click Add expense
FLOW: add -> expenses | click Save
FLOW: expenses -> report | click Report""",
    ),
    (
        "An event RSVP page where guests see event details and reply yes or no",
        """TYPE: web_app
MODULE: Event | Tell guests what is happening
FEATURE: Event details | WHEN a guest opens the invite link | THEN the date, place and description are shown
FEATURE: Edit event details | WHEN the host changes the date or place | THEN guests see the updated details
SCREEN: event | Event | Details of the event
MODULE: Replies | Know who is coming
FEATURE: Reply to the invite | WHEN a guest chooses yes or no and enters a name | THEN the reply is saved
FEATURE: Guest list | WHEN the host opens the guest list | THEN everyone who replied is shown with their answer
FEATURE: Reply count | WHEN the host opens the guest list | THEN the number of yes and no replies is shown
SCREEN: reply | Reply | Name and yes or no
SCREEN: guests | Guest List | Replies so far
FLOW: event -> reply | click RSVP
FLOW: reply -> event | submit reply
FLOW: event -> guests | host clicks Guest list""",
    ),
]


def main():
    out = Path(__file__).resolve().parent / "planning-examples.jsonl"
    rows = []
    for idea, plan in EXAMPLES:
        spec, flow, scenarios = parse_plan(plan)  # raises if the real parser would reject it
        quality = score(idea, spec, flow, scenarios)  # examples must meet the same bar as model output
        if not quality["pass"]:
            raise SystemExit(f"example fails the quality bar: {idea!r}: {quality}")
        rows.append({"idea": idea, "product_type": spec["product_type"], "plan": plan})
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} examples to {out}")


if __name__ == "__main__":
    main()
