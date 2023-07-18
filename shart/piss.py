def printpiss(pisser, pissee):
    lolman = "     ë\n"
    lolman += f"   .-║- <- {pisser} \n"
    lolman += "   ╭╰\\\n"
    lolman += "   ┊/ \\\n"
    lolman += "   ┊\n"
    lolman += f" {pissee}\n"
    lolman = drawbox(lolman, "single")
    pismsg = f"{pissee} just got pissed on by {pisser}."
    finmsg = lolman + pismsg

    for i in finmsg.split("\n"):
        sendquery(channel, i)
