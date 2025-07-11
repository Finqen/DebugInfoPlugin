#include "clang/AST/AST.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/Frontend/FrontendPluginRegistry.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"
#include "clang/Basic/SourceManager.h"
#include "llvm/Support/raw_ostream.h"
#include <vector>
#include <string>
#include <iostream>
#include <fstream>
#include <filesystem>

using namespace clang;
using namespace ast_matchers;

namespace {



class InlinedFunction {
public:
  std::string name;
  int line;
  int column;
};

std::vector<InlinedFunction> inlinedFunctions;

void addInlinedFunction(const std::string& name, int line, int column) {
    InlinedFunction func;
    func.name = name;
    func.line = line;
    func.column = column;
    inlinedFunctions.push_back(func);
}

void writeInlinedFunctionsToJsonFile(const std::string &filename, const std::string &sourcefilename) {
    std::ofstream outFile(filename);
    if (!outFile) {
        llvm::errs() << "Failed to open output file: " << filename << "\n";
        return;
    }

    outFile << "{\n" << "  \"functions\": {\n";
    for (size_t i = 0; i < inlinedFunctions.size(); ++i) {
        const auto &func = inlinedFunctions[i];
        outFile << "    \"" << i << "\": {\n" 
                << "      \"symbol_name\": \"" << func.name << "\",\n"
                << "      \"calling_convention\": \"cdecl\",\n"
                << "      \"return_registers\": [\"eax\", \"edx\"],\n"
                << "      \"clobbered_registers\": [\"ebx\", \"ecx\"],\n"
                << "      \"source_match\": {\n"
                << "        \"confidence\": 1,\n"
                << "        \"line\": " << func.line << ",\n"
                << "        \"function_name\": \"" << func.name << "\",\n"
                << "        \"file\": \"inlined from " << sourcefilename << "\",\n"
                << "        \"return_value\": {\n"
                << "            \"type\": \"int\""  
                << "        },\n"
                << "        \"parameters\": {\n"
                << "          },\n"
                << "        \"local_variables\": {\n"
                << "          }\n"
                << "      }\n"
                //<< "      \"column\": " << func.column << "\n"
                << "    }" << (i + 1 < inlinedFunctions.size() ? "," : "") << "\n";
    }
    outFile << "  }\n" << "}\n";

    outFile.close();
    llvm::errs() << "Wrote " << inlinedFunctions.size()
                 << " inlined functions to " << filename << "\n";
}

class DebugEnhancer : public MatchFinder::MatchCallback {
public:
  void run(const MatchFinder::MatchResult &Result) override {

    /*
    // HANDLE VAR DECL
    if (const VarDecl *VD = Result.Nodes.getNodeAs<VarDecl>("varDecl")) {
      FullSourceLoc FullLocation = Result.Context->getFullLoc(VD->getBeginLoc());
      if (FullLocation.isValid()) {
        llvm::errs() << "Variable declared: " << VD->getNameAsString()
                     << " at " << FullLocation.getSpellingLineNumber()
                     << ":" << FullLocation.getSpellingColumnNumber() << "\n";
      }
    }
    */

    /*
        // HANDLE FUN DECL
    if (const FunctionDecl *FD = Result.Nodes.getNodeAs<FunctionDecl>("funcDecl")) {
      FullSourceLoc FullLocation = Result.Context->getFullLoc(FD->getBeginLoc());
      if (FullLocation.isValid()) {
        addInlinedFunction(FD->getNameAsString(), FullLocation.getSpellingLineNumber(), FullLocation.getSpellingColumnNumber());
        llvm::errs() << "Inlined function found: " << "\n"
                     << "name: " << FD->getNameAsString() << "\n"
                     << "line " << FullLocation.getSpellingLineNumber() << "\n"
                     << "column " << FullLocation.getSpellingColumnNumber() << "\n";
      }
    }
    */

    if (const CallExpr *CE = Result.Nodes.getNodeAs<CallExpr>("callExpr")) {
    const FunctionDecl *FD = CE->getDirectCallee();
    if (FD && FD->isInlineSpecified()) { // Only log inline functions
        FullSourceLoc FullLocation = Result.Context->getFullLoc(CE->getExprLoc());
        if (FullLocation.isValid()) {
            addInlinedFunction(
                FD->getNameAsString(),
                FullLocation.getSpellingLineNumber(),
                FullLocation.getSpellingColumnNumber());

            llvm::errs() << "Inlined function call found:\n"
                         << "callee: " << FD->getNameAsString() << "\n"
                         << "line: " << FullLocation.getSpellingLineNumber() << "\n"
                         << "column: " << FullLocation.getSpellingColumnNumber() << "\n";
        }
      }
    }

  }
};

class DebugEnhancerASTConsumer : public ASTConsumer {
  MatchFinder Matcher;
  DebugEnhancer Handler;

public:
  DebugEnhancerASTConsumer() {
    // Matcher.addMatcher(varDecl(isExpansionInMainFile()).bind("varDecl"), &Handler);
    // Matcher for main file and inlined function
    Matcher.addMatcher(
        callExpr(isExpansionInMainFile()).bind("callExpr"),
        &Handler);
  }

  void HandleTranslationUnit(ASTContext &Context) override {
    Matcher.matchAST(Context);


    const SourceManager &SM = Context.getSourceManager();

    const FileEntry *mainFileEntry = SM.getFileEntryForID(SM.getMainFileID());
    if (!mainFileEntry) {
        llvm::errs() << "Could not get main file entry.\n";
        return;
    }
    
    std::string mainFileName = mainFileEntry->getName().str();
    std::filesystem::path outputPath = mainFileName;
    outputPath.replace_extension(".json");

    writeInlinedFunctionsToJsonFile(outputPath, mainFileName);
  }

};



class DebugEnhancerPluginAction : public PluginASTAction {
protected:
  std::unique_ptr<ASTConsumer> CreateASTConsumer(CompilerInstance &CI,
                                                 llvm::StringRef) override {
    return std::make_unique<DebugEnhancerASTConsumer>();
  }

    bool ParseArgs(const CompilerInstance &CI,
                 const std::vector<std::string> &args) override {
    // No args needed for now
    return true;
  }

  PluginASTAction::ActionType getActionType() override {
    return AddAfterMainAction;
  }
};



} // namespace

static FrontendPluginRegistry::Add<DebugEnhancerPluginAction>
    X("debug-enhancer", "Enhance debugging info (MWE)");

