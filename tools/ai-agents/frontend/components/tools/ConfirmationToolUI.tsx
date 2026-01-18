import { makeAssistantToolUI } from "@assistant-ui/react";
import { Check, X } from "lucide-react";

interface ConfirmationArgs {
  message: string;
}

interface ConfirmationResult {
  confirmed: boolean;
}

export const ConfirmationToolUI = makeAssistantToolUI<ConfirmationArgs, ConfirmationResult>({
  toolName: "ask_confirmation",
  render: ({ args, result, addResult }) => {
    // 1. If result exists, render read-only state
    if (result) {
      return (
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mt-2 p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-100 dark:border-gray-700">
          <div className={`w-5 h-5 rounded-full flex items-center justify-center text-white ${result.confirmed ? 'bg-green-500' : 'bg-red-500'}`}>
            {result.confirmed ? <Check size={12} /> : <X size={12} />}
          </div>
          <span>User {result.confirmed ? "Confirmed" : "Denied"}</span>
        </div>
      );
    }

    // 2. Render interaction buttons
    return (
      <div className="flex flex-col gap-3 p-4 my-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 shadow-sm">
        <p className="font-medium text-gray-800 dark:text-gray-200">{args.message}</p>
        <div className="flex gap-3">
          <button
            onClick={() => addResult({ confirmed: true })}
            className="flex-1 py-2 px-4 bg-primary hover:bg-primary/90 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            <Check size={16} />
            Confirm
          </button>
          <button
            onClick={() => addResult({ confirmed: false })}
            className="flex-1 py-2 px-4 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            <X size={16} />
            Cancel
          </button>
        </div>
      </div>
    );
  },
});
