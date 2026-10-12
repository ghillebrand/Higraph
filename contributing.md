# Contributing
Contributions are welcomed. The project is at an early stage, and so there are some caveats.

## General Principles
1. **This tool is still in the early stages of development**, and the style is evolving. There are sections where the design patterns are still fluid. There are other areas where seemingly strange constructs are in place, to cater for a feature much further down the timeline. Sometimes a whole section of code will be commented out, pending confirmation that there it is not needed, and that it doesn't have some guidance as to why a later bug might appear. Please accept this and be patient with us!
2. **There are not a lot of references for the GUI patterns for this code.** The division of the logic between `QGraphicsScene` and the various `QGraphicsObjects` is still being refined. There may well be 'other' ways of doing things. In this alpha phase, the goal is to establish the overall architecture, and the interaction of all the pieces - some things will only become clear once later elements are added.
3. **GUI testing is manual**. There may be better ways of doing it, but for now, it is manual. There is a script for testing the GUI [here](https://github.com/ghillebrand/Higraph/blob/main/tests/Regression%20Test1.txt). It is not complete, but PRs need to have run through this before submission.

## AI Tools
Contributions may have been assisted by the use generative AI tools. However, the use of such tools does not change our expectations for contributor responsibility, engagement, or code quality.

Note that a number of the design patterns in Higraph are not common, and LLMs do not have the training set to be able to produce them. There are other well established areas.
The following apply to all contributions.

1. **Human ownership and accountability:**
    1. Contributors are responsible for all submitted content, regardless of whether generative AI tools were used.
    2. Contributors must be able to explain all changes during review.
    3. **Licensing:** Contributors are responsible for ensuring all submitted code complies with Higraph's licensing, regardless of whether generative AI tools were used.
2. **Disclosure:** If generative AI tools were used for substantive portions of the contribution, contributors must describe their use in the change description. This also helps downstream citations comply with academic policies that may require disclosure of genAI usage.
3. **Authentic engagement:** The pull request process is collaborative and iterative. Contributors are expected to actively engage with reviewer feedback themselves. Copying and pasting replies to / from a generative AI tool does not count as engaging with the reviewer; contributors are expected to understand the changes they are proposing, not act as message courier for a third party.

> [!IMPORTANT]
> Autonomous workflows ("agents") are not human contributors. Higraph reviewers expect to interact with the human controlling the account, or we will close the PR.
4. **Consistency with Higraph conventions and existing style:** In the context of Generative AI, this particularly means conveying information (comments, documentation, etc) in a style that Higraph uses, and that is appropriate and to the point.

> [!NOTE]
> This policy is significantly inspired by the the AstroPy ["AI-Policy"](https://github.com/astropy/astropy-project/blob/main/policies/ai-policy.md), which has additional details and references that may be useful.
