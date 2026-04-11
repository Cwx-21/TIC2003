import { useEffect, useState } from "react";
import api from "../utils/api";

function SentimentTable({ selectedAsset, backtestId }) {
	const [comments, setComments] = useState([]);
	const [error, setError] = useState("");

	useEffect(() => {
		if (!selectedAsset) return;

		const getComments = async () => {
			try {
				const response = await api.get(`/sentiment/${selectedAsset}/logs`, {
					params: {
						backtest_id: backtestId,
					},
                });

				setComments(response.data.data || []);
				setError("");
			} catch (err) {
				console.error(err);
				setError("Failed to load comments");
			}
		};

		getComments();
	}, [selectedAsset, backtestId]);

	if (!selectedAsset) {
		return null;
	}

	const normalComments = comments.filter((item) => item.content !== "Comment");
	const commentPlaceholders = comments
		.filter((item) => item.content === "Comment")
		.slice(0, 3);

	const displayedComments = comments.filter((item) => item.url);

	return (
		<div className="container">
			<h2>Comments and Sentiment</h2>

			{error && <p>{error}</p>}

			{!error && displayedComments.length === 0 && <p>No comments found.</p>}

			{displayedComments.length > 0 && (
				<div className="sentiment-table-wrapper">
					<table className="sentiment-table">
						<thead>
							<tr>
								<th>Content</th>
								<th>Sentiment Score</th>
							</tr>
						</thead>

						<tbody>
                            {displayedComments.map((item) => (
                                <tr key={item.id}>
                                    <td>
                                        {item.url ? (<a href={item.url} target="_blank" rel="noreferrer" className="comment-link"> {item.content} </a>) : (item.content)}
                                    </td>
                                    <td>{item.sentiment_score}</td>
                                </tr>
                            ))}
                        </tbody>
					</table>
				</div>
			)}
		</div>
	);
}

export default SentimentTable;