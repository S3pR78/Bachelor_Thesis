import * as fs from "node:fs";
import * as path from "node:path";
import { generateDynamicSPARQLPrompt } from "./promptGenerator";

const NLP4RE_TEMPLATE_PATH = path.resolve(__dirname, "../templates/nlp4re-template.json");
const OUTPUT_TXT_PATH = path.resolve(__dirname, "../generated/rendered_prompt.txt");

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
	console.log(`Prompt written to: ${filePath}`);
}

function main(): void {
    const templateMapping = readJsonFile<Record<string, unknown>>(NLP4RE_TEMPLATE_PATH);


	const prompt = generateDynamicSPARQLPrompt(
		templateMapping as any,
		"R1544125",
		"NLP for Requirements Engineering (NLP4RE)",
		"C121001"
	);

	writeToFile(OUTPUT_TXT_PATH, prompt);
	console.log("Prompt generated successfully and saved successfully.");
	console.log(`Template file: ${NLP4RE_TEMPLATE_PATH}`);
	console.log(`Output file: ${OUTPUT_TXT_PATH}`);
	console.log(`prompt length: ${prompt.length}`);
}

main();