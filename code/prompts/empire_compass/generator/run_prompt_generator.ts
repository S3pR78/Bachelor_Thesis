import * as fs from "node:fs";
import * as path from "node:path";
import { generateDynamicSPARQLPrompt } from "./promptGenerator";


const SELECTED_PROFILE_KEY = "empirical_research"; // Change this to select a different profile. When i find the time to implement CLI args, this will be replaced by a command line argument.


type PromptRunProfile = {
	template_path: string;
	template_id: string;
	template_label: string;
	target_class_id: string;
	output_txt_path: string;
};

type PromptRunnerConfig = {
	profiles: Record<string, PromptRunProfile>;
}

const RUNNER_CONFIG_PATH = path.resolve(__dirname, "../config/prompt_runner_config.json");

const REPO_ROOT = path.resolve(__dirname, "../../../..");


function readJsonFile<T>(filePath: string): T {
	const fileContent = fs.readFileSync(filePath, "utf-8");
  	return JSON.parse(fileContent) as T;
}

function ensureDir(dirPath: string): void {
	if (!fs.existsSync(dirPath)) {
		fs.mkdirSync(dirPath, { recursive: true });
	}
}


function writeToFile(filePath: string, content: string): void {
	ensureDir(path.dirname(filePath));
	fs.writeFileSync(filePath, content, "utf-8");
}

function resolveRepoPath(relativePath: string): string {
	if (path.isAbsolute(relativePath)) {
		return relativePath;
	}
	return path.resolve(REPO_ROOT, relativePath);
}

function loadRunnerConfig(filePath: string): PromptRunnerConfig {
	const config = readJsonFile<PromptRunnerConfig>(filePath);
	if (!config.profiles ||  typeof config.profiles !== "object") {
		throw new Error(`Profile '${SELECTED_PROFILE_KEY}' not found in runner config.`);
	}
	return config;
}

function main(): void {
	const runnerConfig = loadRunnerConfig(RUNNER_CONFIG_PATH);
	const profile = runnerConfig.profiles[SELECTED_PROFILE_KEY];
	if (!profile) {
		throw new Error(`Profile '${SELECTED_PROFILE_KEY}' not found in runner config.`);
	}

	const templatePath = resolveRepoPath(profile.template_path);
	const outputTxtPath = resolveRepoPath(profile.output_txt_path);

	const templateMapping = readJsonFile<Record<string, unknown>>(templatePath);

	const prompt = generateDynamicSPARQLPrompt(
		templateMapping as any,
		profile.template_id,
		profile.template_label,
		profile.target_class_id
	);

	writeToFile(outputTxtPath, prompt);

	console.log("Prompt generated and saved successfully.");
	console.log(`Profile:      ${SELECTED_PROFILE_KEY}`);
	console.log(`Config file:  ${RUNNER_CONFIG_PATH}`);
	console.log(`Template:     ${templatePath}`);
	console.log(`Output file:  ${outputTxtPath}`);
	console.log(`Prompt size:  ${prompt.length}`);
}

main();