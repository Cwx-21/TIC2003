import { useEffect, useState } from "react";
import api from "../utils/api";

// Load latest backtest ID and active session ID on mount
function useSession() {
    const [backtestId, setBacktestId] = useState(null);
	const [sessionId, setSessionId] = useState(null);

    useEffect(() => {
		Promise.all([api.get("/backtests"), api.get("/sessions?status=running")])
			.then(([btRes, sesRes]) => {
				setBacktestId(btRes.data.data[0]?.id ?? null);
				setSessionId(sesRes.data.data[0]?.id ?? null);
			})
			.catch(() => {
				// Non-fatal: chart will show empty state
			});
	}, []);

	return { backtestId, sessionId };
}

export default useSession;