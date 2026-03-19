import { useMsal } from "@azure/msal-react";
import { loginRequest } from "../auth/msalConfig";

export default function LoginPage() {
  const { instance } = useMsal();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-blue-100">
      <div className="card max-w-md w-full text-center">
        <div className="mb-8">
          <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Spend Analyzer</h1>
          <p className="text-gray-500 mt-2">
            AI-powered invoice processing and spend analytics
          </p>
        </div>
        <button
          onClick={() => instance.loginRedirect(loginRequest)}
          className="btn-primary w-full text-base py-3"
        >
          Sign in with Microsoft
        </button>
        <p className="text-xs text-gray-400 mt-4">
          Secured with Azure AD Single Sign-On
        </p>
      </div>
    </div>
  );
}
