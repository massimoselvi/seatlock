# Level 1: system context.

systemLandscape "landscape" "Seatlock, the people who use it, and the systems around it." {
    include *
    autolayout tb
}

systemContext seatlock "context" "Level 1. Seatlock and who and what it talks to while it runs." {
    include attendee organizer seatlock email
    autolayout lr
}

systemContext seatlock "delivery" "How code gets built, tested and onto AWS." {
    include operator github aws seatlock
    autolayout lr
}
