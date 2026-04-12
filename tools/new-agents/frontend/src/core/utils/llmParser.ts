export function parseLlmStreamChunk(fullText: string, currentArtifact: string) {
    let chatResponse = '';
    let newArtifact = currentArtifact;
    let action = '';
    let hasArtifactUpdate = false;

    // Parse CHAT
    const chatMatch = fullText.match(/<CHAT>([\s\S]*?)(?:<\/CHAT>|$)/i);
    if (chatMatch) {
        chatResponse = chatMatch[1].trim();
    } else {
        // If no <CHAT> tag yet, just show the raw text
        // Replace all tags that might have started so they don't leak into chat visually
        chatResponse = fullText.replace(/<\/?(?:CHAT|ARTIFACT|ACTION)>/gi, '').trim();
        if (!chatResponse) chatResponse = fullText.replace(/<CHAT>/i, '').trim();
    }

    // Parse ARTIFACT
    const artifactMatch = fullText.match(/<ARTIFACT>([\s\S]*?)(?:<\/ARTIFACT>|$)/i);
    if (artifactMatch) {
        const extractedArtifact = artifactMatch[1].trim();
        if (extractedArtifact && !extractedArtifact.includes('NO_UPDATE')) {
            newArtifact = extractedArtifact;
            hasArtifactUpdate = true;
        }
    }

    // Parse ACTION
    const actionMatch = fullText.match(/<ACTION>([\s\S]*?)(?:<\/ACTION>|$)/i);
    if (actionMatch) {
        action = actionMatch[1].trim();
    }

    return { chatResponse, newArtifact, action, hasArtifactUpdate };
}

/**
 * P0-9: Detect if the ARTIFACT tag was never closed (stream truncated).
 * Call this after the stream ends to check for truncation.
 */
export function detectArtifactTruncation(fullText: string): boolean {
    const hasArtifactOpen = /<ARTIFACT>/i.test(fullText);
    const hasArtifactClose = /<\/ARTIFACT>/i.test(fullText);
    // Truncated if we opened ARTIFACT but never closed it
    return hasArtifactOpen && !hasArtifactClose;
}
