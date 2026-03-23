# Office: news_editor

Inputs: article_in
Outputs: article_out

Agents:
Jordan is an editor.
Riley is a rewriter.

Connections:
article_in's destination is Jordan.
Jordan's rewriter is Riley.
Jordan's discard is discard.
Riley's output is article_out.
