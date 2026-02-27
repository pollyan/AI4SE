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
