import { useEffect, useState } from "react";
import api from "../utils/api";

function useSentimentLogs(selectedAsset, backtestId) {
	const [comments, setComments] = useState([]);
	const [error, setError] = useState("");

	useEffect(() => {
		if (!selectedAsset) {
			setComments([]);
			setError("");
			return;
		}

        const getComments = async () => {
            try {
                setError("");

                const response = await api.get(`/sentiment/${selectedAsset}/logs`, {
                    params: {
                        backtest_id: backtestId,
                    },
                });
                setComments(response.data.data || []);
            } catch (err) {
                console.error(err);
                setError("Failed to load comments");
                setComments([]);
            }
        }

		getComments();
	}, [selectedAsset, backtestId]);

	return { comments, error };
}

export default useSentimentLogs;