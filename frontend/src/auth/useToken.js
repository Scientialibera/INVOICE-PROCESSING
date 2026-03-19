import { useMsal } from "@azure/msal-react";
import { loginRequest } from "./msalConfig";
import { useCallback } from "react";

export function useToken() {
  const { instance, accounts } = useMsal();

  const getToken = useCallback(async () => {
    if (!accounts.length) return null;
    try {
      const response = await instance.acquireTokenSilent({
        ...loginRequest,
        account: accounts[0],
      });
      return response.accessToken;
    } catch {
      const response = await instance.acquireTokenPopup(loginRequest);
      return response.accessToken;
    }
  }, [instance, accounts]);

  return { getToken, account: accounts[0] || null };
}
