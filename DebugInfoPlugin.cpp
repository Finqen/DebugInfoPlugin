#include "clang/AST/AST.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/Frontend/FrontendPluginRegistry.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"
#include "clang/Basic/SourceManager.h"
#include "llvm/Support/raw_ostream.h"

using namespace clang;
using namespace ast_matchers;

namespace {

class DebugEnhancer : public MatchFinder::MatchCallback {
public:
  void run(const MatchFinder::MatchResult &Result) override {

    // HANDLE VAR DECL
    if (const VarDecl *VD = Result.Nodes.getNodeAs<VarDecl>("varDecl")) {
      FullSourceLoc FullLocation = Result.Context->getFullLoc(VD->getBeginLoc());
      if (FullLocation.isValid()) {
        llvm::errs() << "Variable declared: " << VD->getNameAsString()
                     << " at " << FullLocation.getSpellingLineNumber()
                     << ":" << FullLocation.getSpellingColumnNumber() << "\n";
      }
    }

    // HANDLE FUN DECL
    if (const FunctionDecl *FD = Result.Nodes.getNodeAs<FunctionDecl>("funcDecl")) {
      FullSourceLoc FullLocation = Result.Context->getFullLoc(FD->getBeginLoc());
      if (FullLocation.isValid()) {
        llvm::errs() << "Function declared: " << FD->getNameAsString()
                     << " at " << FullLocation.getSpellingLineNumber()
                     << ":" << FullLocation.getSpellingColumnNumber() << "\n";
      }
    }
  }
};

class DebugEnhancerASTConsumer : public ASTConsumer {
  MatchFinder Matcher;
  DebugEnhancer Handler;

public:
  DebugEnhancerASTConsumer() {
    Matcher.addMatcher(varDecl(isExpansionInMainFile()).bind("varDecl"), &Handler);
    Matcher.addMatcher(functionDecl(isExpansionInMainFile()).bind("funcDecl"), &Handler);
  }

  void HandleTranslationUnit(ASTContext &Context) override {
    Matcher.matchAST(Context);
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

