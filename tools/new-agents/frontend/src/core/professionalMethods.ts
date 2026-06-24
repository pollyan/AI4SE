import professionalMethodsData from '../../../professional_methods.json';

type ProfessionalMethod = {
    id: string;
    name: string;
    description: string;
    guidance: string;
};

const PROFESSIONAL_METHODS = professionalMethodsData.methods as ProfessionalMethod[];

export const getProfessionalMethods = (methodIds: readonly string[] = []): ProfessionalMethod[] => {
    return methodIds.map((methodId) => {
        const method = PROFESSIONAL_METHODS.find(candidate => candidate.id === methodId);
        if (!method) {
            throw new Error(`Unknown professional method id: ${methodId}`);
        }
        return method;
    });
};

export const buildProfessionalMethodPromptSection = (
    methodIds: readonly string[] = []
): string => {
    const methods = getProfessionalMethods(methodIds);
    if (methods.length === 0) {
        return '';
    }

    const lines = methods.map(
        method => `- ${method.name}: ${method.description} 使用要求：${method.guidance}`
    );

    return `\n【专业方法参考】\n${lines.join('\n')}\n`;
};
